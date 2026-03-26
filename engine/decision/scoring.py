"""
Categorisation des regles pour reporting / analytics.

Le scoring pondere 0-100 a ete supprime.
Un dossier carte grise est conforme ou il ne l'est pas — pas de "75% bon".

Ce module conserve uniquement le mapping rule_name → categorie
pour le reporting dans le dashboard (ex: "3 blocages identite, 1 warning vehicule").
"""
from __future__ import annotations


def categorize_rule(rule_name: str) -> str | None:
    """Associe un nom de regle a une categorie de reporting."""
    mapping = {
        # VIN
        "vin_coc_facture": "vin",
        "vin_coc_assurance": "vin",
        "vin_cg_vs_da": "vin",
        "immatriculation_coherence": "vin",
        "doublon_vin_interne": "vin",
        # Identite
        "name_cni_facture_nom": "identite",
        "name_cni_permis_nom": "identite",
        "name_cni_permis_prenom": "identite",
        "ddn_cni_permis": "identite",
        "name_cni_assurance_nom": "identite",
        "name_cni_domicile_nom": "identite",
        "vendeur_da_vs_titulaire_cg": "identite",
        "siret_cession_vs_da": "identite",
        # Vehicule
        "marque_coc_facture": "vehicule",
        "energie_coc_facture": "vehicule",
        "cnit_format": "vehicule",
        "puissance_fiscale_coc_cerfa": "vehicule",
        "co2_wltp_source": "vehicule",
        "co2_wltp_nedc_gap": "vehicule",
        "gage_actif": "vehicule",
        "otci_active": "vehicule",
        "vec_status": "vehicule",
        "vei_status": "vehicule",
        "vol_signale": "vehicule",
        "vec_vei_status": "vehicule",
        # Documents / dates
        "facture_date_vs_today": "documents",
        "assurance_active_today": "documents",
        "assurance_delay_after_sale": "documents",
        "cg_date_vs_da_date": "documents",
        "da_date_vs_cession_date": "documents",
        "recepisse_da_delay": "documents",
        "cg_signatures_vs_cotitulaires": "documents",
        "cession_signature_vendeur": "documents",
        "cession_tampon_siret": "documents",
        "ct_validity_at_saisie_siv": "documents",
        # Adresse
        "address_cerfa_vs_domicile": "adresse",
        "address_cerfa_vs_titre_sejour": "adresse",
        # Permis / Age
        "permis_categorie_vehicule": "permis",
        "age_categorie_vehicule": "permis",
    }
    return mapping.get(rule_name)
