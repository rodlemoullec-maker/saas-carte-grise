"""
Bundle par défaut des règles paramétrables.

Ce fichier est embarqué dans le code source du logiciel local. Il sert
de **fallback** si aucun bundle plus récent n'a été téléchargé depuis le
serveur de l'éditeur.

Quand l'éditeur publie une nouvelle version (par exemple suite à une
évolution réglementaire — nouveau bareme malus CO2 2027, nouvelle
puissance fiscale par région, etc.), il :

1. Modifie les valeurs ci-dessous
2. Incrémente la version
3. Génère un bundle JSON signé via scripts/sign_rules_bundle.py
4. Le dépose sur licenses.autodocpro.fr/rules/latest

Les agents installés téléchargent automatiquement la nouvelle version
à leur prochaine vérification (par défaut une fois par jour).
"""
from __future__ import annotations


# ─── Métadonnées du bundle ────────────────────────────────────────────────

DEFAULT_BUNDLE_VERSION = "2026.04.01"
DEFAULT_BUNDLE_DESCRIPTION = "Bundle de référence — release initiale locale"


# ─── Règles par défaut ────────────────────────────────────────────────────

DEFAULT_RULES: dict = {
    "version": DEFAULT_BUNDLE_VERSION,
    "description": DEFAULT_BUNDLE_DESCRIPTION,
    "released_at": "2026-04-01T00:00:00Z",

    # ─── OCR ────────────────────────────────────────────────────────────
    "ocr": {
        # Seuil sous lequel un document est considéré illisible
        "seuil_illisible": 0.40,
        # Seuil sous lequel on émet un avertissement de qualité
        "seuil_avertissement": 0.70,
        # Taille minimale d'image avant upscaling (px)
        "min_dimension_px": 1500,
    },

    # ─── Validité temporelle des documents ─────────────────────────────
    "validite_documents": {
        # Justificatif de domicile : âge maximal en jours
        "domicile_max_age_days": 180,
        # Kbis : âge maximal en jours
        "kbis_max_age_days": 90,
        # Code de cession : âge maximal en jours
        "code_cession_max_age_days": 15,
        # Facture VN avant immatriculation : âge maximal en jours
        "facture_vn_max_age_days": 180,
        # Contrôle technique VO : âge maximal en jours (6 mois)
        "ct_max_age_days": 180,
        # Règle CNI 2004-2013 : extension de validité de 5 ans
        "cni_2004_2013_extension_years": 5,
    },

    # ─── Cohérence inter-documents ──────────────────────────────────────
    "coherence": {
        # Seuils de fuzzy matching sur les noms (en pourcentage)
        "nom_match_auto_threshold": 0.97,
        "nom_match_warning_threshold": 0.85,
        "nom_match_error_threshold": 0.85,
        # Tolérance puissance fiscale (CV) entre COC et Cerfa
        "puissance_cv_warning_delta": 1,
        "puissance_cv_error_delta": 3,
    },

    # ─── Taxes d'immatriculation ────────────────────────────────────────
    "taxes": {
        # Tarif Y1 par cheval fiscal (€) — défaut national, peut être surchargé
        # par une table régionale dans une release future
        "y1_default_per_cv": 43.0,

        # Tarif Y1 régional par département (extrait, à enrichir)
        # Format : code département → tarif €/CV
        "y1_par_departement": {
            "75": 46.15,  # Paris
            "13": 51.20,  # Bouches-du-Rhône
            "69": 43.00,  # Rhône
            "33": 41.00,  # Gironde
            "27": 35.00,  # Eure
            "76": 36.00,  # Seine-Maritime
        },

        # Y3 — Malus CO2 WLTP (barème simplifié 2026)
        # Format : seuils croissants {seuil_g_co2: montant_eur}
        "y3_malus_co2_wltp": {
            "118": 50,
            "120": 75,
            "125": 200,
            "130": 500,
            "140": 983,
            "150": 1504,
            "160": 2049,
            "170": 2818,
            "180": 3760,
            "190": 4818,
            "200": 6017,
            "210": 7462,
            "220": 9132,
            "230": 11078,
            "240": 13361,
            "250": 16100,
            "260": 19000,
            "270": 22000,
            "280": 26000,
            "290": 30000,
            "300": 35000,
            "310": 40000,
            "320": 45000,
            "330": 50000,
            "340": 55000,
            "350": 60000,
        },

        # Y4 — Taxe de gestion fixe (0 € si véhicule électrique)
        "y4_taxe_gestion": 11.0,

        # Y5 — Redevance acheminement
        "y5_redevance_acheminement": 2.76,

        # Y6 — Malus au poids (€/kg au-dessus du seuil)
        "y6_seuil_poids_kg": 1800,
        "y6_eur_par_kg": 10,
    },

    # ─── Catégories de permis ──────────────────────────────────────────
    "permis": {
        # Âge minimum par catégorie
        "age_min_am": 14,
        "age_min_a1": 16,
        "age_min_a2": 18,
        "age_min_b": 18,
        "age_min_a": 20,  # Avec A2 depuis 2 ans
        # Permis B + 125cc : formation 7h obligatoire si permis < 2 ans
        "formation_7h_anciennete_seuil_annees": 2,
        "formation_7h_puissance_max_kw": 11,
        "formation_7h_cylindree_max_cc": 125,
    },

    # ─── Mots-clés de classification ───────────────────────────────────
    # Note : ces mots-clés enrichissent les listes définies dans
    # engine/pipeline/realtime.py (DOC_TYPES). Ils ne les remplacent pas.
    "classification_extra_keywords": {
        "CNI": [],
        "PASSEPORT": [],
        "PERMIS": [],
        "COC": [],
        "FACTURE": [],
        "DOMICILE": [],
        "CG_BARREE": [],
        "CERTIFICAT_CESSION": [],
        "KBIS": [],
        "ASSURANCE": [],
        "ATTESTATION_FORMATION": [],
    },

    # ─── Cas spéciaux à détecter ───────────────────────────────────────
    "cas_speciaux": {
        # Détection de l'hébergement (nom CNI ≠ nom domicile)
        "detection_hebergement_active": True,
        # Détection automatique de la personne morale (présence Kbis)
        "detection_personne_morale_active": True,
        # Détection mineur basée sur date de naissance
        "detection_mineur_active": True,
    },
}


def get_default_bundle() -> dict:
    """Retourne une copie du bundle par défaut (embarqué dans le code)."""
    import copy
    return copy.deepcopy(DEFAULT_RULES)
