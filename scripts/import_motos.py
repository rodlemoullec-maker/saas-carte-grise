"""Import du dataset Kaggle motos dans la table types_mines.

Adapte les données Kaggle aux champs nécessaires pour le CERFA carte grise :
- Genre national (MTL/MTT1/MTT2) calculé depuis la cylindrée
- Énergie (ES/EL) déduite depuis la cylindrée (NaN = électrique)
- Puissance fiscale calculée via la formule administrative
- Puissance kW convertie depuis les HP
"""

import csv
import math
import subprocess
import sys
from pathlib import Path

CSV_FILE = Path(__file__).resolve().parent.parent / "data" / "types_mines" / "motos_kaggle.csv"
DB_NAME = "carte_grise"


def calc_genre_moto(cylindree: float | None) -> str:
    """Détermine le genre national d'une moto selon sa cylindrée."""
    if cylindree is None or cylindree == 0:
        return "MTL"  # Électrique → assimilé MTL sauf si puissance > 11kW
    if cylindree < 125:
        return "MTL"
    if cylindree < 600:
        return "MTT1"
    return "MTT2"


def calc_energie(cylindree: float | None, is_electric: bool) -> str:
    """Détermine le code énergie."""
    if is_electric or cylindree is None or cylindree == 0:
        return "EL"
    return "ES"


def calc_puissance_fiscale(puissance_kw: float | None, cylindree: float | None) -> int:
    """Calcule la puissance fiscale administrative pour une moto.

    Formule : PA = (CO2/45) + (P/40)^1.6
    Pour les motos sans CO2, formule simplifiée :
    PA = max(1, floor(puissance_kw / 5.585))
    Ou si cylindrée connue : PA = cylindrée / 125 arrondi
    """
    if puissance_kw and puissance_kw > 0:
        # Formule simplifiée pour motos
        pa = max(1, math.floor(puissance_kw / 5.585))
        return min(pa, 50)  # Plafonner à 50 CV fiscaux
    if cylindree and cylindree > 0:
        return max(1, round(cylindree / 125))
    return 1


def hp_to_kw(hp: float | None) -> float | None:
    """Convertit les chevaux (HP) en kilowatts."""
    if hp is None or hp == 0:
        return None
    return round(hp * 0.7457, 2)


def parse_float(val: str) -> float | None:
    if not val or val.strip() == "" or val.strip().lower() == "nan":
        return None
    try:
        return float(val.replace(",", ".").strip())
    except (ValueError, TypeError):
        return None


def escape_sql(val: str | None) -> str:
    if not val or str(val).strip() == "" or str(val).strip().lower() == "nan":
        return "NULL"
    return "'" + str(val).replace("'", "''").strip() + "'"


def sql_val(val) -> str:
    if val is None:
        return "NULL"
    return str(val)


def main():
    if not CSV_FILE.exists():
        print(f"ERREUR: {CSV_FILE} non trouvé", file=sys.stderr)
        sys.exit(1)

    sql_statements = []
    seen = set()
    count = 0
    count_elec = 0

    with open(CSV_FILE, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)

        for row in reader:
            brand = row.get("Brand", "").strip().upper()
            model = row.get("Model", "").strip()
            year = row.get("Year", "").strip()
            category = row.get("Category", "").strip()

            if not brand or not model:
                continue

            displacement = parse_float(row.get("Displacement (ccm)", ""))
            power_hp = parse_float(row.get("Power (hp)", ""))
            dry_weight = parse_float(row.get("Dry weight (kg)", ""))

            # Détecter si électrique
            is_electric = (
                displacement is None
                or displacement == 0
                or "electric" in str(row.get("Fuel system", "")).lower()
                or "electric" in category.lower()
            )

            # Générer un CNIT unique pour moto
            cnit_base = f"M_{brand[:3]}_{model[:10]}_{year}".replace(" ", "_").replace("/", "_")
            cnit = cnit_base[:20]

            if cnit in seen:
                continue
            seen.add(cnit)

            # Calculer les champs CERFA
            genre = calc_genre_moto(displacement)
            energie = calc_energie(displacement, is_electric)
            puissance_kw = hp_to_kw(power_hp)
            puissance_fiscale = calc_puissance_fiscale(puissance_kw, displacement)

            # Pour les électriques puissantes, corriger le genre
            if is_electric and puissance_kw and puissance_kw > 11:
                genre = "MTT1"
            if is_electric and puissance_kw and puissance_kw > 35:
                genre = "MTT2"

            cylindree_int = int(displacement) if displacement else None
            poids_int = int(dry_weight) if dry_weight else None

            if is_electric:
                count_elec += 1

            sql = (
                f"INSERT INTO types_mines (cnit, marque, denomination_commerciale, "
                f"genre, carrosserie, energie, cylindree, puissance_fiscale, "
                f"puissance_kw, poids_vide) "
                f"VALUES ({escape_sql(cnit)}, {escape_sql(brand)}, "
                f"{escape_sql(f'{model} ({year})')}, "
                f"{escape_sql(genre)}, 'SOLO', {escape_sql(energie)}, "
                f"{sql_val(cylindree_int)}, {sql_val(puissance_fiscale)}, "
                f"{sql_val(puissance_kw)}, {sql_val(poids_int)}) "
                f"ON CONFLICT (cnit) DO NOTHING;"
            )
            sql_statements.append(sql)
            count += 1

    if not sql_statements:
        print("Aucune moto à importer.")
        return

    # Écrire dans un fichier SQL temporaire
    tmp_sql = CSV_FILE.parent / "_tmp_import_motos.sql"
    with open(tmp_sql, "w", encoding="utf-8") as f:
        f.write("\n".join(sql_statements))

    result = subprocess.run(
        ["psql", DB_NAME, "-f", str(tmp_sql)],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        print(f"ERREUR: {result.stderr[:300]}", file=sys.stderr)

    tmp_sql.unlink(missing_ok=True)

    print(f"Import motos terminé : {count} motos importées ({count_elec} électriques)")

    # Vérification
    result = subprocess.run(
        ["psql", DB_NAME, "-c",
         "SELECT genre, energie, COUNT(*) as nb FROM types_mines "
         "WHERE genre IN ('MTL','MTT1','MTT2') "
         "GROUP BY genre, energie ORDER BY genre, energie;"],
        capture_output=True,
        text=True,
    )
    print("\nRépartition motos en base :")
    print(result.stdout)

    result = subprocess.run(
        ["psql", DB_NAME, "-c", "SELECT COUNT(*) as total FROM types_mines;"],
        capture_output=True,
        text=True,
    )
    print("Total véhicules en base :")
    print(result.stdout)


if __name__ == "__main__":
    main()
