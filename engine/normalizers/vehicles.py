"""
Normalisation des données véhicule.

Tables de mapping pour énergie, marques, carrosseries.
"""
from __future__ import annotations

# Table de mapping énergie → code normalisé
ENERGIE_MAPPING: dict[str, str] = {
    # Essence
    "essence": "essence", "petrol": "essence", "gasoline": "essence",
    "sp95": "essence", "sp98": "essence", "e10": "essence", "e85": "essence",
    "sans plomb": "essence", "superethanol": "essence",
    # Diesel
    "diesel": "diesel", "gazole": "diesel", "gasoil": "diesel",
    "gas oil": "diesel", "tdi": "diesel", "hdi": "diesel",
    "dci": "diesel", "bluehdi": "diesel",
    # Électrique
    "electrique": "electrique", "électrique": "electrique",
    "electric": "electrique", "bev": "electrique", "ev": "electrique",
    "100% electrique": "electrique",
    # Hybride
    "hybride": "hybride", "hybrid": "hybride", "hev": "hybride",
    "full hybrid": "hybride", "mild hybrid": "hybride",
    # Hybride rechargeable
    "hybride rechargeable": "hybride_rechargeable",
    "phev": "hybride_rechargeable", "plug-in hybrid": "hybride_rechargeable",
    "plug in hybrid": "hybride_rechargeable", "rechargeable": "hybride_rechargeable",
    # GPL
    "gpl": "gpl", "lpg": "gpl", "autogas": "gpl", "gaz de petrole": "gpl",
    # GNV
    "gnv": "gnv", "cng": "gnv", "gaz naturel": "gnv",
    "compressed natural gas": "gnv",
    # Hydrogène
    "hydrogene": "hydrogene", "hydrogen": "hydrogene", "fcev": "hydrogene",
}

# Alias marques (OCR / abréviations connues)
MARQUE_ALIASES: dict[str, str] = {
    "vw": "VOLKSWAGEN", "volkswagen": "VOLKSWAGEN",
    "bmw": "BMW",
    "mercedes": "MERCEDES-BENZ", "mercedes benz": "MERCEDES-BENZ",
    "psa": "PEUGEOT",  # contexte
    "renault": "RENAULT", "dacia": "DACIA",
    "citroen": "CITROEN", "citroën": "CITROEN",
    "peugeot": "PEUGEOT",
    "fiat": "FIAT",
    "ford": "FORD",
    "opel": "OPEL",
    "toyota": "TOYOTA",
    "honda": "HONDA",
    "hyundai": "HYUNDAI",
    "kia": "KIA",
    "skoda": "SKODA", "škoda": "SKODA",
    "seat": "SEAT",
    "audi": "AUDI",
    "tesla": "TESLA",
    "volvo": "VOLVO",
    "nissan": "NISSAN",
    "mitsubishi": "MITSUBISHI",
    "suzuki": "SUZUKI",
    "mazda": "MAZDA",
}

# Codes carrosserie EU → libellé
CARROSSERIE_EU: dict[str, str] = {
    "AA": "Berline",
    "AB": "Hatchback",
    "AC": "Break / Estate",
    "AD": "Coupé",
    "AE": "Cabriolet / Décapotable",
    "AF": "Multi-purpose vehicle (MPV)",
    "AG": "SUV / Tout-terrain",
    "AN": "Fourgon",
    "SA": "Motocycle",
    "SB": "Tricycle",
    "L1e": "Cyclomoteur 2 roues",
    "L2e": "Cyclomoteur 3 roues",
    "L3e": "Motocycle",
    "L4e": "Motocycle avec side-car",
    "L5e": "Tricycle à moteur",
    "L6e": "Quadricycle léger",
    "L7e": "Quadricycle lourd",
}


def normalize_energie(value: str) -> str | None:
    """Normalise une valeur d'énergie vers le code standard."""
    key = value.lower().strip()
    return ENERGIE_MAPPING.get(key)


def normalize_marque(value: str) -> str:
    """Normalise un nom de marque (uppercase + alias)."""
    key = value.lower().strip()
    return MARQUE_ALIASES.get(key, value.upper().strip())


def energies_match(energie_a: str, energie_b: str) -> bool:
    """Vérifie la cohérence entre deux valeurs d'énergie (sources différentes)."""
    na = normalize_energie(energie_a)
    nb = normalize_energie(energie_b)
    if na is None or nb is None:
        return False
    return na == nb
