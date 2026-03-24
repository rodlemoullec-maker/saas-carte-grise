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
}


def get_triggered_blocking_rules(cross_check_results: list[CrossCheckResult]) -> list[str]:
    """
    Identifie les règles bloquantes déclenchées à partir des résultats de croisements.
    """
    triggered = []

    for result in cross_check_results:
        if result.status == CrossCheckStatus.FAIL:
            if result.rule_name == "vin_coc_facture":
                triggered.append("vin_coc_facture_mismatch")
            elif result.rule_name == "vin_coc_assurance" and result.confidence == 0.0:
                triggered.append("vin_coc_assurance_mismatch")
            elif result.rule_name == "assurance_active_today":
                triggered.append("insurance_expired")
            elif result.rule_name == "assurance_not_active":
                triggered.append("insurance_not_active")

    return list(set(triggered))
