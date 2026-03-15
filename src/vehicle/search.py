"""Moteur de recherche véhicule multi-sources.

Combine 3 sources pour obtenir la fiche technique la plus complète :
1. Base types mines (CNIT → caractéristiques techniques)
2. Base stock interne (véhicules de l'entreprise)
3. Décodeur VIN (constructeur, année, pays)
"""

from src.vehicle import vin_decoder, types_mines, stock


def search(
    vin: str = "",
    immatriculation: str = "",
    cnit: str = "",
    tvv: str = "",
    marque: str = "",
    modele: str = "",
    use_stock: bool = False,
) -> dict:
    """Recherche un véhicule en combinant toutes les sources.

    Priorité : types mines (CNIT) → décodeur VIN.
    Le stock interne est optionnel (use_stock=True) — par défaut
    on est intermédiaire et le véhicule n'est pas dans notre stock.

    Args:
        vin: Numéro VIN (17 caractères).
        immatriculation: Plaque d'immatriculation.
        cnit: Code CNIT.
        tvv: Code TVV (Type Variante Version, champ D.2 carte grise).
        marque: Marque du véhicule.
        modele: Modèle ou dénomination commerciale.
        use_stock: Si True, cherche aussi dans le stock interne.

    Returns:
        Dict fusionné avec toutes les données disponibles.
    """
    result = {
        "vin": vin,
        "immatriculation": immatriculation,
        "sources": [],
    }

    # Source 1 : Stock interne (optionnel — désactivé par défaut)
    stock_data = None
    if use_stock:
        if vin:
            stock_data = stock.search_by_vin(vin)
        if not stock_data and immatriculation:
            stock_data = stock.search_by_immatriculation(immatriculation)

    if stock_data:
        result["sources"].append("stock_interne")
        result.update({
            "marque": stock_data.get("marque", ""),
            "modele": stock_data.get("modele", ""),
            "cnit": stock_data.get("cnit", ""),
            "km": stock_data.get("km"),
            "prix_vente": float(stock_data["prix_vente"]) if stock_data.get("prix_vente") else None,
            "statut_stock": stock_data.get("statut", ""),
            "date_premiere_immat": str(stock_data["date_premiere_immat"]) if stock_data.get("date_premiere_immat") else None,
        })
        # Utiliser le CNIT du stock pour la recherche types mines
        if not cnit and stock_data.get("cnit"):
            cnit = stock_data["cnit"]

    # Source 2 : Base types mines
    mines_data = None
    if cnit:
        mines_data = types_mines.search_by_cnit(cnit)
    if not mines_data and tvv:
        mines_data = types_mines.search_by_tvv(tvv)
    if not mines_data and marque:
        results = types_mines.search_by_marque_modele(marque, modele)
        if results:
            mines_data = results[0]

    if mines_data:
        result["sources"].append("types_mines")
        result.update({
            "cnit": mines_data.get("cnit", result.get("cnit", "")),
            "marque": mines_data.get("marque", result.get("marque", "")),
            "denomination_commerciale": mines_data.get("denomination_commerciale", ""),
            "genre": mines_data.get("genre", ""),
            "carrosserie": mines_data.get("carrosserie", ""),
            "energie": mines_data.get("energie", ""),
            "cylindree": mines_data.get("cylindree"),
            "puissance_fiscale": mines_data.get("puissance_fiscale"),
            "puissance_kw": float(mines_data["puissance_kw"]) if mines_data.get("puissance_kw") else None,
            "co2": mines_data.get("co2"),
            "nb_places": mines_data.get("nb_places"),
            "poids_vide": mines_data.get("poids_vide"),
            "ptac": mines_data.get("ptac"),
        })

    # Source 3 : Décodeur VIN
    if vin and vin_decoder.is_valid_vin(vin):
        vin_data = vin_decoder.decode_vin(vin)
        if "error" not in vin_data:
            result["sources"].append("vin_decoder")
            if not result.get("marque"):
                result["marque"] = vin_data.get("constructeur", "")
            result["constructeur_vin"] = vin_data.get("constructeur", "")
            result["pays_origine"] = vin_data.get("pays_origine", "")
            result["annee_modele"] = vin_data.get("annee_modele")

    # Indicateur de complétude
    essential_fields = ["marque", "genre", "energie", "puissance_fiscale"]
    filled = sum(1 for f in essential_fields if result.get(f))
    result["completude"] = f"{filled}/{len(essential_fields)}"

    return result
