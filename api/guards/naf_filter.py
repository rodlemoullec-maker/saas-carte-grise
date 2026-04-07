"""
Filtre NAF — vérifie que le SIRET du pro correspond à une activité automobile légitime.
Bloque les mandataires carte grise en ligne (concurrents).

Utilise l'API Recherche Entreprises (data.gouv.fr) — gratuite, sans clé.
"""
from __future__ import annotations

import logging
import httpx

logger = logging.getLogger(__name__)

SIRENE_API = "https://recherche-entreprises.api.gouv.fr/search"

# Codes NAF autorisés — activités automobile légitimes
NAF_AUTORISES = {
    # Commerce de véhicules
    "45.11Z",  # Commerce de voitures et de véhicules légers
    "45.19Z",  # Commerce d'autres véhicules automobiles
    "45.40Z",  # Commerce de motocycles
    # Entretien et réparation
    "45.20A",  # Entretien et réparation de véhicules automobiles légers
    "45.20B",  # Entretien et réparation d'autres véhicules automobiles
    # Commerce de pièces
    "45.31Z",  # Commerce de gros d'équipements automobiles
    "45.32Z",  # Commerce de détail d'équipements automobiles
    # Location
    "77.11A",  # Location de courte durée de voitures
    "77.11B",  # Location de longue durée de voitures
    # Activités de conseil / gestion automobile
    "70.22Z",  # Conseil pour les affaires et autres conseils de gestion
    "64.19Z",  # Autres intermédiations monétaires
    # Construction / import
    "29.10Z",  # Construction de véhicules automobiles
    "29.20Z",  # Fabrication de carrosseries et remorques
    "46.11Z",  # Intermédiaires du commerce en matières premières agricoles (importateurs parfois)
}

# Codes NAF interdits — mandataires CG en ligne / prestataires de service administratif
NAF_INTERDITS = {
    "82.99Z",  # Autres activités de soutien aux entreprises (mandataires CG en ligne)
    "82.11Z",  # Services administratifs combinés de bureau
    "63.99Z",  # Autres services d'information
    "62.01Z",  # Programmation informatique (éditeurs de logiciels CG concurrents)
    "62.02A",  # Conseil en systèmes et logiciels informatiques
    "63.12Z",  # Portails internet
    "96.09Z",  # Autres services personnels (fourre-tout souvent utilisé par les mandataires)
}

# Mots-clés suspects dans le nom de l'entreprise
NOMS_SUSPECTS = [
    "carte grise", "cartegrise", "immatriculation", "mandataire carte",
    "eplaque", "siv pro", "cerfa", "carte-grise", "guichet carte",
]


async def verifier_siret(siret: str) -> dict:
    """
    Vérifie un SIRET via l'API Recherche Entreprises.

    Retourne :
    - status: "ok" | "refuse" | "alerte" | "introuvable"
    - raison: explication
    - naf: code NAF trouvé
    - nom: nom de l'entreprise
    """
    siret_clean = siret.replace(" ", "").replace(".", "")

    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(SIRENE_API, params={"q": siret_clean})
            data = resp.json()
    except Exception as e:
        logger.warning(f"[NAF] Erreur API SIRENE pour {siret_clean}: {e}")
        return {"status": "alerte", "raison": "Vérification SIRENE indisponible — vérification manuelle recommandée.", "naf": None, "nom": None}

    if not data.get("results"):
        return {"status": "introuvable", "raison": f"SIRET {siret_clean} introuvable dans la base SIRENE.", "naf": None, "nom": None}

    entreprise = data["results"][0]
    nom = entreprise.get("nom_complet", "")
    naf = entreprise.get("activite_principale") or entreprise.get("siege", {}).get("activite_principale") or ""

    # Vérification nom suspect
    nom_lower = nom.lower()
    for suspect in NOMS_SUSPECTS:
        if suspect in nom_lower:
            return {
                "status": "refuse",
                "raison": f"L'entreprise \"{nom}\" semble être un service de carte grise en ligne. AutoDoc Pro est réservé aux professionnels de l'automobile (vendeurs, garages, agents habilités).",
                "naf": naf,
                "nom": nom,
            }

    # Vérification NAF interdit
    if naf in NAF_INTERDITS:
        return {
            "status": "refuse",
            "raison": f"Le code NAF {naf} de \"{nom}\" ne correspond pas à une activité automobile. AutoDoc Pro est réservé aux professionnels de l'automobile.",
            "naf": naf,
            "nom": nom,
        }

    # Vérification NAF autorisé
    if naf in NAF_AUTORISES:
        return {
            "status": "ok",
            "raison": f"Activité automobile confirmée ({naf}).",
            "naf": naf,
            "nom": nom,
        }

    # NAF ni autorisé ni interdit → alerte (vérification manuelle recommandée)
    return {
        "status": "alerte",
        "raison": f"Le code NAF {naf} de \"{nom}\" n'est pas une activité automobile classique. Inscription possible mais surveillée.",
        "naf": naf,
        "nom": nom,
    }
