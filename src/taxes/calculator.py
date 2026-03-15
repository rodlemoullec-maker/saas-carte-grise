"""Calcul des taxes carte grise (Y1-Y6).

Calcule toutes les composantes de la taxe carte grise :
- Y1 : Taxe régionale (puissance fiscale × tarif région)
- Y3 : Taxe formation professionnelle (1% de Y1, pour les pros)
- Y4 : Malus CO2 (véhicules neufs VP uniquement)
- Y5 : Malus au poids (véhicules neufs VP > 1800 kg)
- Y6 : Taxe fixe d'acheminement (11€)
"""

from datetime import date

from config.tax_rates import (
    TARIF_REGIONAL_PAR_CV,
    TAXE_FIXE_Y6,
    ENERGIES_EXONEREES_Y1,
    ENERGIES_DEMI_TARIF_Y1,
    TAUX_FORMATION_PRO,
    MALUS_CO2_SEUIL,
    MALUS_CO2_BAREME,
    MALUS_MASSE_SEUIL,
    MALUS_MASSE_TARIF_PAR_KG,
    MALUS_MASSE_PLAFOND,
    GENRES_EXEMPTES_MALUS,
)


def calculer_taxes(
    puissance_fiscale: int,
    region: str,
    energie: str = "",
    co2: int = 0,
    masse: int = 0,
    genre: str = "VP",
    est_neuf: bool = False,
    est_professionnel: bool = True,
) -> dict:
    """Calcule toutes les taxes pour une demande de carte grise.

    Args:
        puissance_fiscale: Puissance administrative en CV.
        region: Clé de la région (ex: "ile_de_france").
        energie: Code énergie (ES, GO, EL, EH, etc.).
        co2: Émissions CO2 en g/km.
        masse: Masse du véhicule en kg.
        genre: Genre national (VP, MTL, MTT1, MTT2, REM, etc.).
        est_neuf: True si première immatriculation (malus applicable).
        est_professionnel: True si demande par un professionnel (Y3 applicable).

    Returns:
        Dict avec Y1, Y3, Y4, Y5, Y6, total et détails.
    """
    result = {
        "Y1_taxe_regionale": 0.0,
        "Y3_taxe_formation": 0.0,
        "Y4_malus_co2": 0.0,
        "Y5_malus_masse": 0.0,
        "Y6_taxe_fixe": TAXE_FIXE_Y6,
        "total": 0.0,
        "details": {},
    }

    # --- Y1 : Taxe régionale ---
    tarif = TARIF_REGIONAL_PAR_CV.get(region, 0)
    if tarif == 0:
        result["details"]["Y1_warning"] = f"Région inconnue: {region}"

    y1 = puissance_fiscale * tarif

    # Exonérations énergie
    energie_upper = energie.upper().strip()
    if energie_upper in ENERGIES_EXONEREES_Y1:
        y1 = 0.0
        result["details"]["Y1_exoneration"] = f"Véhicule {energie_upper} exonéré"
    elif energie_upper in ENERGIES_DEMI_TARIF_Y1:
        y1 = y1 * 0.5
        result["details"]["Y1_demi_tarif"] = f"Véhicule hybride {energie_upper} : demi-tarif"

    result["Y1_taxe_regionale"] = round(y1, 2)
    result["details"]["Y1_calcul"] = f"{puissance_fiscale} CV × {tarif}€ = {y1:.2f}€"

    # --- Y3 : Taxe formation professionnelle ---
    if est_professionnel:
        y3 = round(y1 * TAUX_FORMATION_PRO, 2)
        result["Y3_taxe_formation"] = y3
        result["details"]["Y3_calcul"] = f"{y1:.2f}€ × {TAUX_FORMATION_PRO} = {y3:.2f}€"
    else:
        result["details"]["Y3_info"] = "Non applicable (particulier)"

    # --- Y4 : Malus CO2 ---
    y4 = _calcul_malus_co2(co2, genre, est_neuf)
    result["Y4_malus_co2"] = y4
    if y4 > 0:
        result["details"]["Y4_calcul"] = f"CO2 {co2} g/km → malus {y4:.2f}€"
    elif genre in GENRES_EXEMPTES_MALUS:
        result["details"]["Y4_info"] = f"Genre {genre} exempté de malus CO2"
    elif not est_neuf:
        result["details"]["Y4_info"] = "Véhicule d'occasion : pas de malus CO2"
    else:
        result["details"]["Y4_info"] = f"CO2 {co2} g/km : sous le seuil ({MALUS_CO2_SEUIL} g/km)"

    # --- Y5 : Malus masse ---
    y5 = _calcul_malus_masse(masse, genre, est_neuf)
    result["Y5_malus_masse"] = y5
    if y5 > 0:
        result["details"]["Y5_calcul"] = f"Masse {masse} kg → malus {y5:.2f}€"
    elif genre in GENRES_EXEMPTES_MALUS:
        result["details"]["Y5_info"] = f"Genre {genre} exempté de malus masse"
    elif not est_neuf:
        result["details"]["Y5_info"] = "Véhicule d'occasion : pas de malus masse"
    else:
        result["details"]["Y5_info"] = f"Masse {masse} kg : sous le seuil ({MALUS_MASSE_SEUIL} kg)"

    # --- Y6 : Taxe fixe ---
    result["details"]["Y6_info"] = f"Redevance d'acheminement : {TAXE_FIXE_Y6}€"

    # --- Total ---
    result["total"] = round(
        result["Y1_taxe_regionale"]
        + result["Y3_taxe_formation"]
        + result["Y4_malus_co2"]
        + result["Y5_malus_masse"]
        + result["Y6_taxe_fixe"],
        2,
    )

    return result


def _calcul_malus_co2(co2: int, genre: str, est_neuf: bool) -> float:
    """Calcule le malus CO2 (Y4)."""
    # Pas de malus si occasion, si pas VP, ou si CO2 sous le seuil
    if not est_neuf or genre in GENRES_EXEMPTES_MALUS or co2 < MALUS_CO2_SEUIL:
        return 0.0

    for co2_min, co2_max, montant in MALUS_CO2_BAREME:
        if co2_min <= co2 <= co2_max:
            return float(montant)

    return 0.0


def _calcul_malus_masse(masse: int, genre: str, est_neuf: bool) -> float:
    """Calcule le malus au poids (Y5)."""
    if not est_neuf or genre in GENRES_EXEMPTES_MALUS or masse <= MALUS_MASSE_SEUIL:
        return 0.0

    malus = (masse - MALUS_MASSE_SEUIL) * MALUS_MASSE_TARIF_PAR_KG
    return float(min(malus, MALUS_MASSE_PLAFOND))


def get_regions() -> list[str]:
    """Retourne la liste des régions disponibles."""
    return sorted(TARIF_REGIONAL_PAR_CV.keys())
