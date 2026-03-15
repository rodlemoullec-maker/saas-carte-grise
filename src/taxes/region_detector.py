"""Détection automatique de la région depuis le code postal.

Mapping des départements français vers les régions pour le calcul
de la taxe régionale carte grise.
"""

# Département (2 premiers chiffres du code postal) → région
DEPARTEMENT_TO_REGION = {
    # Auvergne-Rhône-Alpes
    "01": "auvergne_rhone_alpes", "03": "auvergne_rhone_alpes",
    "07": "auvergne_rhone_alpes", "15": "auvergne_rhone_alpes",
    "26": "auvergne_rhone_alpes", "38": "auvergne_rhone_alpes",
    "42": "auvergne_rhone_alpes", "43": "auvergne_rhone_alpes",
    "63": "auvergne_rhone_alpes", "69": "auvergne_rhone_alpes",
    "73": "auvergne_rhone_alpes", "74": "auvergne_rhone_alpes",
    # Bourgogne-Franche-Comté
    "21": "bourgogne_franche_comte", "25": "bourgogne_franche_comte",
    "39": "bourgogne_franche_comte", "58": "bourgogne_franche_comte",
    "70": "bourgogne_franche_comte", "71": "bourgogne_franche_comte",
    "89": "bourgogne_franche_comte", "90": "bourgogne_franche_comte",
    # Bretagne
    "22": "bretagne", "29": "bretagne", "35": "bretagne", "56": "bretagne",
    # Centre-Val de Loire
    "18": "centre_val_de_loire", "28": "centre_val_de_loire",
    "36": "centre_val_de_loire", "37": "centre_val_de_loire",
    "41": "centre_val_de_loire", "45": "centre_val_de_loire",
    # Corse
    "20": "corse", "2A": "corse", "2B": "corse",
    # Grand Est
    "08": "grand_est", "10": "grand_est", "51": "grand_est",
    "52": "grand_est", "54": "grand_est", "55": "grand_est",
    "57": "grand_est", "67": "grand_est", "68": "grand_est",
    "88": "grand_est",
    # Hauts-de-France
    "02": "hauts_de_france", "59": "hauts_de_france",
    "60": "hauts_de_france", "62": "hauts_de_france",
    "80": "hauts_de_france",
    # Île-de-France
    "75": "ile_de_france", "77": "ile_de_france",
    "78": "ile_de_france", "91": "ile_de_france",
    "92": "ile_de_france", "93": "ile_de_france",
    "94": "ile_de_france", "95": "ile_de_france",
    # Normandie
    "14": "normandie", "27": "normandie", "50": "normandie",
    "61": "normandie", "76": "normandie",
    # Nouvelle-Aquitaine
    "16": "nouvelle_aquitaine", "17": "nouvelle_aquitaine",
    "19": "nouvelle_aquitaine", "23": "nouvelle_aquitaine",
    "24": "nouvelle_aquitaine", "33": "nouvelle_aquitaine",
    "40": "nouvelle_aquitaine", "47": "nouvelle_aquitaine",
    "64": "nouvelle_aquitaine", "79": "nouvelle_aquitaine",
    "86": "nouvelle_aquitaine", "87": "nouvelle_aquitaine",
    # Occitanie
    "09": "occitanie", "11": "occitanie", "12": "occitanie",
    "30": "occitanie", "31": "occitanie", "32": "occitanie",
    "34": "occitanie", "46": "occitanie", "48": "occitanie",
    "65": "occitanie", "66": "occitanie", "81": "occitanie",
    "82": "occitanie",
    # Pays de la Loire
    "44": "pays_de_la_loire", "49": "pays_de_la_loire",
    "53": "pays_de_la_loire", "72": "pays_de_la_loire",
    "85": "pays_de_la_loire",
    # Provence-Alpes-Côte d'Azur
    "04": "provence_alpes_cote_azur", "05": "provence_alpes_cote_azur",
    "06": "provence_alpes_cote_azur", "13": "provence_alpes_cote_azur",
    "83": "provence_alpes_cote_azur", "84": "provence_alpes_cote_azur",
    # Outre-mer
    "971": "guadeloupe", "972": "martinique", "973": "guyane",
    "974": "la_reunion", "976": "mayotte",
}


def detect_region(code_postal: str) -> str:
    """Détecte la région à partir du code postal.

    Args:
        code_postal: Code postal (5 chiffres).

    Returns:
        Clé de la région (ex: "ile_de_france") ou "ile_de_france" par défaut.
    """
    if not code_postal:
        return "ile_de_france"

    cp = str(code_postal).strip().replace(" ", "")

    # Outre-mer (3 premiers chiffres)
    if len(cp) >= 3 and cp[:3] in DEPARTEMENT_TO_REGION:
        return DEPARTEMENT_TO_REGION[cp[:3]]

    # Corse (2A, 2B)
    if len(cp) >= 2:
        dept = cp[:2]

        # Corse
        if dept == "20":
            return "corse"

        if dept in DEPARTEMENT_TO_REGION:
            return DEPARTEMENT_TO_REGION[dept]

    return "ile_de_france"
