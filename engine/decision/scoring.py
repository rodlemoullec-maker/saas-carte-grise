"""
Calcul du score de confiance global du dossier.
"""
from __future__ import annotations

from engine.models.decision import CrossCheckResult, CrossCheckStatus

# Pondération des critères (total = 100)
SCORE_WEIGHTS: dict[str, float] = {
    "vin_consistency": 30.0,
    "identity_consistency": 20.0,
    "document_validity": 20.0,
    "vehicle_coherence": 15.0,
    "address_validity": 10.0,
    "driving_license": 5.0,
}


def compute_score(cross_check_results: list[CrossCheckResult]) -> float:
    """
    Calcule le score global (0–100) à partir des résultats de croisements.

    Logique :
    - PASS → contribution pleine au poids
    - WARNING → contribution partielle (50%)
    - FAIL → contribution nulle
    - SKIPPED → ignoré (poids redistribué)
    """
    category_scores: dict[str, list[float]] = {k: [] for k in SCORE_WEIGHTS}

    for result in cross_check_results:
        category = _map_rule_to_category(result.rule_name)
        if category is None:
            continue

        if result.status == CrossCheckStatus.PASS:
            category_scores[category].append(1.0)
        elif result.status == CrossCheckStatus.WARNING:
            category_scores[category].append(0.5)
        elif result.status == CrossCheckStatus.FAIL:
            category_scores[category].append(0.0)

    total_score = 0.0
    total_weight = 0.0

    for category, weight in SCORE_WEIGHTS.items():
        scores = category_scores.get(category, [])
        if not scores:
            continue  # Pas de données pour cette catégorie
        avg = sum(scores) / len(scores)
        total_score += avg * weight
        total_weight += weight

    if total_weight == 0:
        return 0.0

    return round((total_score / total_weight) * 100, 2)


def _map_rule_to_category(rule_name: str) -> str | None:
    """Associe un nom de règle à une catégorie de scoring."""
    mapping = {
        "vin_coc_facture": "vin_consistency",
        "vin_coc_assurance": "vin_consistency",
        "marque_coc_facture": "vehicle_coherence",
        "energie_coc_facture": "vehicle_coherence",
        "name_cni_facture_nom": "identity_consistency",
        "name_cni_permis_nom": "identity_consistency",
        "name_cni_permis_prenom": "identity_consistency",
        "ddn_cni_permis": "identity_consistency",
        "name_cni_assurance_nom": "identity_consistency",
        "name_cni_domicile_nom": "identity_consistency",
        "facture_date_vs_today": "document_validity",
        "assurance_active_today": "document_validity",
    }
    return mapping.get(rule_name)
