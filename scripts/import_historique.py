"""Import des fichiers ADEME historiques (2012-2015) dans types_mines.

Ces fichiers contiennent les véhicules commercialisés en France avec CNIT,
couvrant le marché de l'occasion.
"""

import csv
import subprocess
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent / "data" / "types_mines"
DB_NAME = "carte_grise"

# Mapping des colonnes par année vers nos colonnes standardisées
COLUMN_MAPS = {
    "2012": {
        "marque": "lib_mrq",
        "denomination": "dscom",
        "cnit": "cnit",
        "tvv": "tvv",
        "energie": "typ_cbr",
        "puissance_fiscale": "puiss_admin_98",
        "puissance_kw": "puiss_max",
        "co2": "co2",
        "poids_vide": "masse_ordma_min",
        "carrosserie": "Carrosserie",
    },
    "2013": {
        "marque": "Marque",
        "denomination": "D\xe9signation commerciale",
        "cnit": "CNIT",
        "tvv": "Type Variante Version (TVV)",
        "energie": "Carburant",
        "puissance_fiscale": "Puissance administrative",
        "puissance_kw": "Puissance maximale (kW)",
        "co2": "CO2 (g/km)",
        "poids_vide": "masse vide euro min (kg)",
        "carrosserie": "Carrosserie",
    },
    "2014": {
        "marque": "lib_mrq",
        "denomination": "dscom",
        "cnit": "cnit",
        "tvv": "tvv",
        "energie": "cod_cbr",
        "puissance_fiscale": "puiss_admin_98",
        "puissance_kw": "puiss_max",
        "co2": "co2",
        "poids_vide": "masse_ordma_min",
        "carrosserie": "Carrosserie",
    },
    "2015": {
        "marque": "lib_mrq_doss",
        "denomination": "dscom",
        "cnit": "cnit",
        "tvv": "tvv",
        "energie": "energ",
        "puissance_fiscale": "puiss_admin",
        "puissance_kw": "puiss_max",
        "co2": "co2_mixte",
        "poids_vide": "masse_ordma_min",
        "carrosserie": None,
    },
}

FILES = {
    "2012": BASE_DIR / "tmp_2012" / "BASE CL MAJ JUIN 2012.csv",
    "2013": BASE_DIR / "tmp_2013" / "cl_JUIN_2013-complet3.csv",
    "2014": BASE_DIR / "tmp_2014" / "mars-2014-complete.csv",
    "2015": BASE_DIR / "tmp_2015" / "fic_etiq_edition_40-mars-2015.csv",
}


def parse_int(val: str) -> str:
    if not val or val.strip() == "":
        return "NULL"
    try:
        cleaned = val.replace(",", ".").replace(" ", "").strip()
        return str(int(float(cleaned)))
    except (ValueError, TypeError):
        return "NULL"


def parse_float(val: str) -> str:
    if not val or val.strip() == "":
        return "NULL"
    try:
        cleaned = val.replace(",", ".").replace(" ", "").strip()
        return str(float(cleaned))
    except (ValueError, TypeError):
        return "NULL"


def escape_sql(val: str) -> str:
    if not val or val.strip() == "":
        return "NULL"
    return "'" + val.replace("'", "''").strip() + "'"


def map_energie(code: str) -> str:
    code = code.upper().strip()
    mapping = {
        "GO": "GO", "ES": "ES", "EL": "EL", "EH": "EH",
        "GH": "GH", "GP": "GP", "GL": "GL", "FE": "EL",
        "ES/GN": "EG", "ES/GP": "EG", "GN": "GN", "GN/ES": "EG",
        "DIESEL": "GO", "GAZOLE": "GO", "ESSENCE": "ES",
        "ELECTRIC": "EL", "ELECTRIQUE": "EL",
    }
    return mapping.get(code, code[:2] if code else "XX")


def detect_encoding(filepath: Path) -> str:
    """Essaie utf-8, sinon latin-1. Lit le fichier entier pour valider."""
    for enc in ["utf-8-sig", "utf-8"]:
        try:
            with open(filepath, "r", encoding=enc) as f:
                f.read()  # Lire tout le fichier pour valider
            return enc
        except (UnicodeDecodeError, UnicodeError):
            continue
    return "latin-1"


def import_file(year: str, filepath: Path, col_map: dict) -> int:
    if not filepath.exists():
        print(f"  SKIP: {filepath} non trouvé")
        return 0

    encoding = detect_encoding(filepath)
    print(f"  Encodage détecté: {encoding}")

    sql_statements = []
    seen_cnit = set()
    count = 0

    with open(filepath, "r", encoding=encoding) as f:
        reader = csv.DictReader(f, delimiter=";")

        for row in reader:
            cnit = row.get(col_map["cnit"], "").strip()
            if not cnit or cnit in seen_cnit or len(cnit) < 3:
                continue
            seen_cnit.add(cnit)

            marque = row.get(col_map["marque"], "").strip()
            denomination = row.get(col_map["denomination"], "").strip()
            energie_raw = row.get(col_map["energie"], "").strip()
            puissance_fiscale = row.get(col_map["puissance_fiscale"], "")
            puissance_kw = row.get(col_map["puissance_kw"], "")
            co2 = row.get(col_map["co2"], "")
            poids_vide = row.get(col_map["poids_vide"], "")
            carrosserie_col = col_map.get("carrosserie")
            carrosserie = row.get(carrosserie_col, "") if carrosserie_col else ""

            if not marque:
                continue

            energie = map_energie(energie_raw)

            sql = (
                f"INSERT INTO types_mines (cnit, marque, denomination_commerciale, "
                f"genre, carrosserie, energie, puissance_fiscale, puissance_kw, "
                f"co2, poids_vide) "
                f"VALUES ({escape_sql(cnit)}, {escape_sql(marque)}, "
                f"{escape_sql(denomination)}, 'VP', {escape_sql(carrosserie)}, "
                f"{escape_sql(energie)}, {parse_int(puissance_fiscale)}, "
                f"{parse_float(puissance_kw)}, {parse_int(co2)}, "
                f"{parse_int(poids_vide)}) "
                f"ON CONFLICT (cnit) DO NOTHING;"
            )
            sql_statements.append(sql)
            count += 1

    if not sql_statements:
        print(f"  Aucune donnée à importer pour {year}")
        return 0

    # Écrire dans un fichier SQL temporaire puis exécuter
    tmp_sql = BASE_DIR / f"_tmp_import_{year}.sql"
    with open(tmp_sql, "w", encoding="utf-8") as f:
        f.write("\n".join(sql_statements))

    result = subprocess.run(
        ["psql", DB_NAME, "-f", str(tmp_sql)],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        print(f"  ERREUR: {result.stderr[:300]}", file=sys.stderr)

    tmp_sql.unlink(missing_ok=True)
    return count


def main():
    total = 0

    for year in sorted(FILES.keys()):
        filepath = FILES[year]
        col_map = COLUMN_MAPS[year]
        print(f"\nImport {year}: {filepath.name}")
        count = import_file(year, filepath, col_map)
        print(f"  → {count} véhicules uniques (CNIT)")
        total += count

    print(f"\n{'='*50}")
    print(f"Total importé: {total} véhicules")

    # Vérification
    result = subprocess.run(
        ["psql", DB_NAME, "-c",
         "SELECT COUNT(*) as total FROM types_mines;"],
        capture_output=True,
        text=True,
    )
    print(f"\nTotal en base:")
    print(result.stdout)

    # Aperçu par marque
    result = subprocess.run(
        ["psql", DB_NAME, "-c",
         "SELECT marque, COUNT(*) as nb FROM types_mines "
         "GROUP BY marque ORDER BY nb DESC LIMIT 15;"],
        capture_output=True,
        text=True,
    )
    print("Top 15 marques:")
    print(result.stdout)


if __name__ == "__main__":
    main()
