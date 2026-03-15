"""Décodeur VIN — table WMI locale.

Le VIN (Vehicle Identification Number) est un code de 17 caractères :
- Positions 1-3 : WMI (World Manufacturer Identifier) → constructeur + pays
- Position 9 : Chiffre de contrôle (Amérique du Nord) ou libre (Europe)
- Position 10 : Année-modèle
- Position 11 : Usine d'assemblage
- Positions 12-17 : Numéro de série
"""

# Table WMI : 3 premiers caractères du VIN → constructeur
WMI_TABLE = {
    # France
    "VF1": "Renault",
    "VF2": "Renault",
    "VF3": "Peugeot",
    "VF4": "Talbot",
    "VF6": "Renault Trucks",
    "VF7": "Citroën",
    "VF8": "Matra/Alpine",
    "VF9": "Bugatti",
    "VNE": "Renault",
    "VNK": "Toyota (France)",
    "VR1": "Dacia (France)",
    "VR3": "Peugeot",
    "VR7": "Citroën",
    # Allemagne
    "WBA": "BMW",
    "WBS": "BMW M",
    "WBY": "BMW (électrique)",
    "WDB": "Mercedes-Benz",
    "WDC": "Mercedes-Benz (SUV)",
    "WDD": "Mercedes-Benz",
    "WDF": "Mercedes-Benz (utilitaire)",
    "WF0": "Ford (Allemagne)",
    "WMA": "MAN",
    "WME": "Smart",
    "WMW": "Mini",
    "WP0": "Porsche",
    "WP1": "Porsche (SUV)",
    "WUA": "Audi Sport",
    "WVW": "Volkswagen",
    "WV1": "Volkswagen (utilitaire)",
    "WV2": "Volkswagen (bus)",
    "WAU": "Audi",
    "WA1": "Audi (SUV)",
    "WDA": "Daimler",
    # Japon
    "JF1": "Subaru",
    "JF2": "Subaru",
    "JHM": "Honda",
    "JH2": "Honda (moto)",
    "JH3": "Honda (moto)",
    "JKA": "Kawasaki",
    "JMZ": "Mazda",
    "JN1": "Nissan",
    "JN6": "Nissan (utilitaire)",
    "JT2": "Toyota",
    "JTE": "Toyota",
    "JTD": "Toyota",
    "JYA": "Yamaha",
    "JS1": "Suzuki",
    "JS2": "Suzuki",
    # Italie
    "ZAM": "Maserati",
    "ZAP": "Piaggio",
    "ZAR": "Alfa Romeo",
    "ZCF": "Iveco",
    "ZDM": "Ducati",
    "ZFA": "Fiat",
    "ZFF": "Ferrari",
    "ZHW": "Lamborghini",
    "ZLA": "Lancia",
    # Royaume-Uni
    "SAJ": "Jaguar",
    "SAL": "Land Rover",
    "SAR": "Rover",
    "SCA": "Rolls-Royce",
    "SCB": "Bentley",
    "SCF": "Aston Martin",
    "SFZ": "McLaren",
    "SMT": "Triumph",
    # Corée du Sud
    "KMH": "Hyundai",
    "KNA": "Kia",
    "KNM": "Renault Korea (Samsung)",
    # Espagne
    "VSS": "Seat",
    # Suède
    "YV1": "Volvo",
    "YS2": "Scania",
    # République Tchèque
    "TMB": "Škoda",
    # États-Unis
    "1G1": "Chevrolet",
    "1FA": "Ford",
    "1FM": "Ford (SUV)",
    "1FT": "Ford (truck)",
    "1HD": "Harley-Davidson",
    "2HM": "Hyundai (USA)",
    "3VW": "Volkswagen (Mexique)",
    "5YJ": "Tesla",
    "7SA": "Tesla",
    # Inde
    "MA3": "Suzuki (Inde)",
    "MAJ": "Mahindra",
    # Chine
    "LFV": "FAW-Volkswagen",
    "LSG": "SAIC GM",
    "LVS": "Ford (Chine)",
}

# Position 10 du VIN → année-modèle
YEAR_CODES = {
    "A": 2010, "B": 2011, "C": 2012, "D": 2013, "E": 2014,
    "F": 2015, "G": 2016, "H": 2017, "J": 2018, "K": 2019,
    "L": 2020, "M": 2021, "N": 2022, "P": 2023, "R": 2024,
    "S": 2025, "T": 2026, "V": 2027, "W": 2028, "X": 2029,
    "Y": 2030,
    "1": 2001, "2": 2002, "3": 2003, "4": 2004, "5": 2005,
    "6": 2006, "7": 2007, "8": 2008, "9": 2009,
}


def decode_vin(vin: str) -> dict:
    """Décode un VIN et retourne les informations disponibles.

    Args:
        vin: Numéro VIN (17 caractères).

    Returns:
        Dict avec constructeur, pays, année_modele, usine, numero_serie.
    """
    if not vin or len(vin) != 17:
        return {"error": f"VIN invalide (longueur: {len(vin) if vin else 0}, attendu: 17)"}

    vin = vin.upper().strip()
    wmi = vin[:3]

    constructeur = WMI_TABLE.get(wmi)
    if not constructeur:
        # Essayer avec les 2 premiers caractères (certains WMI sont partiels)
        for key, val in WMI_TABLE.items():
            if vin.startswith(key[:2]) and key[:2] == wmi[:2]:
                constructeur = val
                break

    # Déterminer le pays d'origine
    pays = _get_country(vin[0])

    # Année-modèle (position 10)
    year_code = vin[9]
    annee = YEAR_CODES.get(year_code)

    return {
        "vin": vin,
        "wmi": wmi,
        "constructeur": constructeur or "Inconnu",
        "pays_origine": pays,
        "annee_modele": annee,
        "code_usine": vin[10],
        "numero_serie": vin[11:17],
        "vds": vin[3:9],  # Vehicle Descriptor Section
    }


def _get_country(first_char: str) -> str:
    """Détermine le pays d'origine à partir du 1er caractère du VIN."""
    countries = {
        "1": "États-Unis", "2": "Canada", "3": "Mexique",
        "4": "États-Unis", "5": "États-Unis",
        "6": "Australie", "7": "Nouvelle-Zélande",
        "8": "Argentine", "9": "Brésil",
        "J": "Japon", "K": "Corée du Sud",
        "L": "Chine", "M": "Inde",
        "S": "Royaume-Uni", "T": "Suisse",
        "V": "France", "W": "Allemagne",
        "X": "Russie", "Y": "Suède",
        "Z": "Italie",
    }
    return countries.get(first_char.upper(), "Inconnu")


def is_valid_vin(vin: str) -> bool:
    """Vérifie si un VIN est syntaxiquement valide."""
    if not vin or len(vin) != 17:
        return False
    vin = vin.upper()
    # Le VIN ne contient pas I, O, Q (confusion avec 1, 0)
    invalid_chars = set("IOQ")
    return all(c.isalnum() and c not in invalid_chars for c in vin)
