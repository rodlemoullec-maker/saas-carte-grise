"""
Calcul du score de confiance global du dossier.

Les ponderations sont configurables via config/scoring.yaml
et peuvent etre overrides par type de dossier (VN vs VO).
"""
from __future__ import annotations

from pathlib import Path

from engine.models.decision import CrossCheckResult, CrossCheckStatus

# Ponderation par defaut (fallback si YAML absent)
_DEFAULT_WEIGHTS: dict[str, float] = {
    "vin_consistency": 30.0,
    "identity_consistency": 20.0,
    "document_validity": 20.0,
    "vehicle_coherence": 15.0,
    "address_validity": 10.0,
    "driving_license": 5.0,
}

# Cache des configs chargees
_loaded_configs: dict[str, dict[str, float]] = {}


def _load_scoring_config() -> dict:
    """Charge la config scoring depuis le YAML."""
    config_path = Path(__file__).parent.parent.parent / "config" / "scoring.yaml"
    if config_path.exists():
        try:
            import yaml
            with open(config_path) as f:
                return yaml.safe_load(f)
        except ImportError:
            pass  # PyYAML pas installe — utiliser les defauts
        except Exception:
            pass
    return {}


def get_weights(dossier_type: str | None = None) -> dict[str, float]:
    """
    Retourne les ponderations de scoring.

    Args:
        dossier_type: "VN" ou "VO" pour un override specifique.
                      None pour les ponderations par defaut.
    """
    if not _loaded_configs:
        raw = _load_scoring_config()
        _loaded_configs["default"] = raw.get("default", _DEFAULT_WEIGHTS)
        _loaded_configs["VN"] = raw.get("vn_override", _loaded_configs["default"])
        _loaded_configs["VO"] = raw.get("vo_override", _loaded_configs["default"])

    if dossier_type and dossier_type.upper() in _loaded_configs:
        return _loaded_configs[dossier_type.upper()]
    return _loaded_configs.get("default", _DEFAULT_WEIGHTS)


# Expose pour compatibilite
SCORE_WEIGHTS = _DEFAULT_WEIGHTS


def compute_score(
    cross_check_results: list[CrossCheckResult],
    dossier_type: str | None = None,
) -> float:
    """
    Calcule le score global (0–100) à partir des résultats de croisements.

    Logique :
    - PASS → contribution pleine au poids
    - WARNING → contribution partielle (50%)
    - FAIL → contribution nulle
    - SKIPPED → ignoré (poids redistribué)
    """
    weights = get_weights(dossier_type)
    category_scores: dict[str, list[float]] = {k: [] for k in weights}

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

    for category, weight in weights.items():
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
        "assurance_delay_after_sale": "document_validity",
        # VO — chaîne propriété / cohérence
        "vin_cg_vs_da": "vin_consistency",
        "vendeur_da_vs_titulaire_cg": "identity_consistency",
        "siret_cession_vs_da": "identity_consistency",
        "cg_date_vs_da_date": "document_validity",
        "da_date_vs_cession_date": "document_validity",
        "recepisse_da_delay": "document_validity",
        "cg_signatures_vs_cotitulaires": "document_validity",
        "cession_signature_vendeur": "document_validity",
        "cession_tampon_siret": "document_validity",
        "ct_validity_at_saisie_siv": "document_validity",
        # SIV status — pondérés en cohérence véhicule
        "gage_actif": "vehicle_coherence",
        "otci_active": "vehicle_coherence",
        "vec_status": "vehicle_coherence",
        "vei_status": "vehicle_coherence",
        "vol_signale": "vehicle_coherence",
        "doublon_vin_interne": "vin_consistency",
        "vec_vei_status": "vehicle_coherence",
        # Adresse
        "address_cerfa_vs_domicile": "address_validity",
        "address_cerfa_vs_titre_sejour": "address_validity",
        # COC / Cerfa cohérence technique
        "cnit_format": "vehicle_coherence",
        "puissance_fiscale_coc_cerfa": "vehicle_coherence",
        "co2_wltp_source": "vehicle_coherence",
        "co2_wltp_nedc_gap": "vehicle_coherence",
        # Permis / Age
        "permis_categorie_vehicule": "driving_license",
        "age_categorie_vehicule": "driving_license",
    }
    return mapping.get(rule_name)
