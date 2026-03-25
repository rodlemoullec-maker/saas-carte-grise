"""
Règles bloquantes du moteur de décision.

Une règle bloquante court-circuite le pipeline et force un REJET ou FRAUDE
indépendamment du score global.
"""
from __future__ import annotations

from dataclasses import dataclass

from engine.models.decision import CrossCheckResult, CrossCheckStatus


@dataclass
class BlockingRule:
    code: str
    message: str
    is_fraud_related: bool = False


# ─── Registre des règles bloquantes ──────────────────────────────────────────

BLOCKING_RULES: dict[str, BlockingRule] = {
    "vin_coc_facture_mismatch": BlockingRule(
        code="vin_coc_facture_mismatch",
        message="VIN différent entre COC et Facture — incohérence documentaire critique",
        is_fraud_related=True,
    ),
    "vin_already_registered": BlockingRule(
        code="vin_already_registered",
        message="Ce VIN est déjà enregistré au SIV — le véhicule n'est pas neuf",
        is_fraud_related=True,
    ),
    "identity_document_expired": BlockingRule(
        code="identity_document_expired",
        message="Pièce d'identité expirée depuis plus de 5 ans",
    ),
    "insurance_expired": BlockingRule(
        code="insurance_expired",
        message="L'attestation d'assurance est expirée à la date de la demande",
    ),
    "insurance_not_active": BlockingRule(
        code="insurance_not_active",
        message="L'assurance ne prend effet qu'après la date de la demande",
    ),
    "siret_invalid": BlockingRule(
        code="siret_invalid",
        message="SIRET du vendeur invalide (format ou clé de contrôle incorrects)",
    ),
    "siret_inactive": BlockingRule(
        code="siret_inactive",
        message="SIRET du vendeur correspondant à une entreprise radiée ou inactive",
    ),
    "fraud_indicator": BlockingRule(
        code="fraud_indicator",
        message="Indicateur de fraude détecté — dossier bloqué, intervention agent obligatoire",
        is_fraud_related=True,
    ),
    "missing_mandatory_document": BlockingRule(
        code="missing_mandatory_document",
        message="Document obligatoire manquant",
    ),
    "driving_license_category_mismatch": BlockingRule(
        code="driving_license_category_mismatch",
        message="Catégorie de permis insuffisante pour ce type de véhicule",
    ),
    "buyer_underage": BlockingRule(
        code="buyer_underage",
        message="L'acheteur est mineur — immatriculation impossible",
    ),
    "vin_format_invalid": BlockingRule(
        code="vin_format_invalid",
        message="Format de VIN invalide (longueur, caractères interdits)",
    ),
    # ─── Règles VO ────────────────────────────────────────────────────────────
    "cg_non_barree": BlockingRule(
        code="cg_non_barree",
        message="Carte grise non barrée en diagonale — transfert de propriété impossible",
    ),
    "cg_barree_date_missing": BlockingRule(
        code="cg_barree_date_missing",
        message="Date ou heure de vente absente sur la carte grise barrée",
    ),
    "cg_barree_signature_missing": BlockingRule(
        code="cg_barree_signature_missing",
        message="Signatures insuffisantes sur la carte grise barrée",
    ),
    "ct_critique": BlockingRule(
        code="ct_critique",
        message="Contrôle technique défavorable critique (R) — véhicule dangereux, vente interdite",
    ),
    "ct_too_old": BlockingRule(
        code="ct_too_old",
        message="Contrôle technique expiré à la date de saisie SIV",
    ),
    "da_missing": BlockingRule(
        code="da_missing",
        message="Déclaration d'achat (D-05) absente — obligatoire pour les pros",
    ),
    "attestation_pro_missing": BlockingRule(
        code="attestation_pro_missing",
        message="Attestation de vérification d'identité pro absente (D-31) — obligation légale SIV",
    ),
    "gage_actif": BlockingRule(
        code="gage_actif",
        message="Gage actif sur le véhicule — transfert de propriété bloqué",
    ),
    "otci_active": BlockingRule(
        code="otci_active",
        message="Opposition au Transfert de Carte Grise (OTCI) active — transfert impossible",
    ),
    "vec_status": BlockingRule(
        code="vec_status",
        message="Véhicule Économiquement Compromis (VEC) — expertise obligatoire avant circulation",
    ),
    "vei_status": BlockingRule(
        code="vei_status",
        message="Véhicule Économiquement Irréparable (VEI) — immatriculation impossible",
    ),
    "vol_signale": BlockingRule(
        code="vol_signale",
        message="ALERTE FRAUDE — Véhicule signalé volé dans la base nationale",
        is_fraud_related=True,
    ),
    "doublon_vin_interne": BlockingRule(
        code="doublon_vin_interne",
        message="VIN déjà présent dans un dossier actif — possible double soumission",
    ),
    "chaine_propriete_mismatch": BlockingRule(
        code="chaine_propriete_mismatch",
        message="Chaîne de propriété incohérente — vendeur DA ≠ titulaire CG barrée",
        is_fraud_related=True,
    ),
    "dates_vo_incoherentes": BlockingRule(
        code="dates_vo_incoherentes",
        message="Dates VO incohérentes : CG barrée / DA / cession non chronologiques",
        is_fraud_related=True,
    ),
    "vin_cg_da_mismatch": BlockingRule(
        code="vin_cg_da_mismatch",
        message="VIN différent entre la CG barrée et la DA — incohérence critique",
        is_fraud_related=True,
    ),
}


def get_triggered_blocking_rules(cross_check_results: list[CrossCheckResult]) -> list[str]:
    """
    Identifie les règles bloquantes déclenchées à partir des résultats de croisements.
    """
    triggered = []

    _RULE_MAP: dict[str, str] = {
        "vin_coc_facture": "vin_coc_facture_mismatch",
        "vin_coc_assurance": "vin_coc_assurance_mismatch",
        "assurance_active_today": "insurance_expired",
        "assurance_not_active": "insurance_not_active",
        # VO
        "vin_cg_vs_da": "vin_cg_da_mismatch",
        "vendeur_da_vs_titulaire_cg": "chaine_propriete_mismatch",
        "cg_date_vs_da_date": "dates_vo_incoherentes",
        "da_date_vs_cession_date": "dates_vo_incoherentes",
        "cg_signatures_vs_cotitulaires": "cg_barree_signature_missing",
        "cession_signature_vendeur": "cg_barree_signature_missing",
        "ct_validity_at_saisie_siv": "ct_too_old",
        # SIV status
        "gage_actif": "gage_actif",
        "otci_active": "otci_active",
        "vec_status": "vec_status",
        "vei_status": "vei_status",
        "vol_signale": "vol_signale",
        "doublon_vin_interne": "doublon_vin_interne",
    }

    for result in cross_check_results:
        if result.status == CrossCheckStatus.FAIL:
            blocking_code = _RULE_MAP.get(result.rule_name)
            if blocking_code:
                triggered.append(blocking_code)

    return list(set(triggered))
