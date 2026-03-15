"""Import du fichier ADEME Car Labelling CSV dans la table types_mines."""

import csv
import subprocess
import sys
from pathlib import Path

CSV_FILE = Path(__file__).resolve().parent.parent / "data" / "types_mines" / "ademe_car_labelling.csv"
DB_NAME = "carte_grise"


def parse_int(val: str) -> str:
    """Convertit une valeur en entier ou NULL."""
    if not val or val.strip() == "":
        return "NULL"
    try:
        return str(int(float(val.replace(",", "."))))
    except (ValueError, TypeError):
        return "NULL"


def parse_float(val: str) -> str:
    """Convertit une valeur en float ou NULL."""
    if not val or val.strip() == "":
        return "NULL"
    try:
        return str(float(val.replace(",", ".")))
    except (ValueError, TypeError):
        return "NULL"


def escape_sql(val: str) -> str:
    """Échappe les apostrophes pour SQL."""
    if not val or val.strip() == "":
        return "NULL"
    return "'" + val.replace("'", "''").strip() + "'"


def map_energie(energie_ademe: str) -> str:
    """Mappe les codes énergie ADEME vers les codes carte grise."""
    mapping = {
        "ESSENCE": "ES",
        "DIESEL": "GO",
        "ELECTRIC": "EL",
        "ESS+ELEC HNR": "EH",
        "ESS+ELEC HR": "EH",
        "GAZ+ELEC HNR": "GH",
        "GAZ+ELEC HR": "GH",
        "DIESEL+ELEC HNR": "GH",
        "DIESEL+ELEC HR": "GH",
        "GAZ": "GP",
        "HYDROGENE": "HY",
        "ESS+GAZ": "EG",
    }
    return mapping.get(energie_ademe.upper().strip(), energie_ademe[:2].upper())


def main():
    if not CSV_FILE.exists():
        print(f"ERREUR: Fichier non trouvé: {CSV_FILE}", file=sys.stderr)
        sys.exit(1)

    sql_statements = []
    seen_cnit = set()
    count = 0

    with open(CSV_FILE, "r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f, delimiter=";")

        for row in reader:
            marque = row.get("Marque", "")
            denomination = row.get("Description Commerciale", "")
            modele = row.get("Modèle", "")
            energie = row.get("Energie", "")
            carrosserie = row.get("Carrosserie", "")
            cylindree = row.get("Cylindrée", "")
            puissance_fiscale = row.get("Puissance fiscale", "")
            puissance_kw = row.get("Puissance maximale", "")
            co2_min = row.get("CO2 vitesse mixte Min", "")
            co2_max = row.get("CO2 vitesse mixte Max", "")
            poids_min = row.get("Masse OM Min", "")
            poids_max = row.get("Masse OM Max", "")
            gamme = row.get("Gamme", "")

            # Générer un CNIT synthétique (marque + modèle + énergie + cylindrée)
            cnit_base = f"{marque[:3]}_{modele}_{energie[:3]}_{cylindree}".replace(" ", "_")
            cnit = cnit_base[:20]

            if cnit in seen_cnit or not marque:
                continue
            seen_cnit.add(cnit)

            # Prendre le CO2 moyen
            co2 = co2_min if co2_min else co2_max
            poids = poids_min if poids_min else poids_max

            energie_code = map_energie(energie)

            sql = (
                f"INSERT INTO types_mines (cnit, marque, denomination_commerciale, "
                f"genre, carrosserie, energie, cylindree, puissance_fiscale, "
                f"puissance_kw, co2, poids_vide) "
                f"VALUES ({escape_sql(cnit)}, {escape_sql(marque)}, "
                f"{escape_sql(denomination)}, 'VP', {escape_sql(carrosserie)}, "
                f"{escape_sql(energie_code)}, {parse_int(cylindree)}, "
                f"{parse_int(puissance_fiscale)}, {parse_float(puissance_kw)}, "
                f"{parse_int(co2)}, {parse_int(poids)}) "
                f"ON CONFLICT (cnit) DO NOTHING;"
            )
            sql_statements.append(sql)
            count += 1

    full_sql = "\n".join(sql_statements)

    result = subprocess.run(
        ["psql", DB_NAME, "-c", full_sql],
        capture_output=True,
        text=True,
    )

    if result.returncode != 0:
        print(f"ERREUR: {result.stderr}", file=sys.stderr)
        sys.exit(1)

    print(f"Import terminé : {count} véhicules importés.")

    # Vérification
    result = subprocess.run(
        ["psql", DB_NAME, "-c", "SELECT COUNT(*) as total FROM types_mines;"],
        capture_output=True,
        text=True,
    )
    print(result.stdout)


if __name__ == "__main__":
    main()
