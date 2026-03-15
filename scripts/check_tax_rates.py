"""Vérification et mise à jour des barèmes taxes carte grise.

Compare les barèmes en vigueur avec ceux configurés et alerte
si une mise à jour est nécessaire.

Les barèmes changent généralement au 1er janvier de chaque année.
Sources officielles :
- Tarifs régionaux : service-public.fr
- Malus CO2 : code des impositions sur les biens et services
- Malus masse : loi de finances
"""

import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from config.tax_rates import (
    TARIF_REGIONAL_PAR_CV,
    MALUS_CO2_SEUIL,
    MALUS_CO2_BAREME,
    MALUS_MASSE_SEUIL,
    MALUS_MASSE_TARIF_PAR_KG,
    TAXE_FIXE_Y6,
)


def check():
    today = date.today()
    config_file = Path(__file__).resolve().parent.parent / "config" / "tax_rates.py"

    print("  === Vérification barèmes taxes ===")
    print(f"  Date du jour : {today}")
    print(f"  Fichier config : {config_file}")
    print()

    # Lire l'année dans le commentaire du fichier
    with open(config_file, "r") as f:
        content = f.read()

    # Chercher l'année dans le fichier
    import re
    year_match = re.search(r"(\d{4})", content.split("\n")[2] if len(content.split("\n")) > 2 else "")
    config_year = int(year_match.group(1)) if year_match else None

    warnings = []

    # 1. Vérifier si les barèmes sont à jour (année)
    if config_year and config_year < today.year:
        warnings.append(
            f"ATTENTION : Barèmes datés de {config_year}, nous sommes en {today.year}. "
            f"Vérifiez si les tarifs régionaux et malus ont changé."
        )
    elif config_year:
        print(f"  Année barèmes : {config_year} ✓")

    # 2. Vérifier les tarifs régionaux
    nb_regions = len(TARIF_REGIONAL_PAR_CV)
    print(f"  Régions configurées : {nb_regions}")
    if nb_regions < 13:
        warnings.append(f"Seulement {nb_regions} régions configurées (13 métropole + 5 outre-mer attendues)")

    # Vérifier les valeurs aberrantes
    for region, tarif in TARIF_REGIONAL_PAR_CV.items():
        if tarif <= 0:
            warnings.append(f"Tarif à 0 pour {region}")
        if tarif > 100:
            warnings.append(f"Tarif anormalement élevé pour {region} : {tarif}€/CV")

    # 3. Vérifier le malus CO2
    print(f"  Seuil malus CO2 : {MALUS_CO2_SEUIL} g/km")
    print(f"  Tranches malus CO2 : {len(MALUS_CO2_BAREME)}")
    if MALUS_CO2_BAREME:
        max_malus = max(m[2] for m in MALUS_CO2_BAREME)
        print(f"  Malus CO2 max : {max_malus}€")

    # 4. Vérifier le malus masse
    print(f"  Seuil malus masse : {MALUS_MASSE_SEUIL} kg")
    print(f"  Tarif malus masse : {MALUS_MASSE_TARIF_PAR_KG}€/kg")

    # 5. Taxe fixe
    print(f"  Taxe fixe Y6 : {TAXE_FIXE_Y6}€")

    # Afficher les warnings
    if warnings:
        print()
        print("  ⚠ ALERTES :")
        for w in warnings:
            print(f"    → {w}")
        print()
        print("  Pour mettre à jour les barèmes :")
        print(f"    1. Modifier {config_file}")
        print("    2. Sources officielles :")
        print("       - Tarifs régionaux : https://www.service-public.fr/particuliers/vosdroits/F19211")
        print("       - Malus CO2 : https://www.service-public.fr/particuliers/vosdroits/F35947")
        print("       - Malus masse : https://www.service-public.fr/particuliers/vosdroits/F35948")
    else:
        print()
        print("  ✓ Barèmes à jour")


if __name__ == "__main__":
    check()
