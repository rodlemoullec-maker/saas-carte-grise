"""
Méta-validateurs de cohérence (V-24 à V-28).

Ces validateurs agrègent les résultats des cross-checks (C-rules) pour
produire des verdicts de verrouillage au niveau V-rule. Ils servent
d'adaptateurs entre le pipeline de cross-checks et le moteur de décision.

V-24 : VIN incohérent (agrège C-06, C-07)
V-25 : Identité incohérente (agrège C-01 à C-05)
V-26 : Chaîne de propriété brisée (agrège C-11)
V-27 : Permis ≠ véhicule (agrège C-15)
V-28 : Âge incompatible (agrège C-16)
"""
from __future__ import annotations

from engine.models.decision import CrossCheckResult, CrossCheckStatus
from engine.validators.base import BaseValidator, ValidationLevel, ValidationResult


class CoherenceMetaValidator(BaseValidator):
    """
    Transforme une liste de CrossCheckResult en ValidationResult agrégé.

    Chaque méta-validateur (V-24 à V-28) définit les rule_names qu'il surveille.
    Si un FAIL est détecté → BLOCKING. Si un WARNING → WARNING. Sinon → valid.
    """

    def __init__(self, v_code: str, v_message: str, watched_rules: list[str]):
        self.v_code = v_code
        self.v_message = v_message
        self.watched_rules = set(watched_rules)

    def validate(self, cross_check_results: list[CrossCheckResult]) -> ValidationResult:
        result = ValidationResult(valid=True)

        relevant = [r for r in cross_check_results if r.rule_name in self.watched_rules]

        if not relevant:
            return result  # Pas de données — on ne peut pas conclure

        failures = [r for r in relevant if r.status == CrossCheckStatus.FAIL]
        warnings = [r for r in relevant if r.status == CrossCheckStatus.WARNING]

        if failures:
            details = "; ".join(
                f"{r.rule_name}: {r.detail or f'{r.source_a} vs {r.source_b}'}"
                for r in failures
            )
            result.add_error(
                code=self.v_code,
                message=f"{self.v_message} — {len(failures)} échec(s) détecté(s)",
                level=ValidationLevel.BLOCKING,
                field=self.v_code,
                value=details,
                correction_action="Vérifier les documents concernés et corriger les incohérences",
            )

        if warnings:
            details = "; ".join(
                f"{r.rule_name}: {r.detail or 'vérification recommandée'}"
                for r in warnings
            )
            result.add_error(
                code=f"{self.v_code}_WARNING",
                message=f"{self.v_message} — {len(warnings)} avertissement(s)",
                level=ValidationLevel.WARNING,
                field=self.v_code,
                value=details,
            )

        return result


# Instances pré-configurées pour chaque V-rule de cohérence
# Le pipeline les appelle avec les résultats des cross-checks correspondants

VINCoherenceValidator = CoherenceMetaValidator(
    v_code="V-24",
    v_message="VIN incohérent entre documents",
    watched_rules=[
        "vin_coc_facture",           # C-06 — VIN COC ↔ Facture
        "vin_coc_assurance",         # C-06 — VIN COC ↔ Assurance
        "vin_cg_vs_da",             # C-06 — VIN CG ↔ DA
        "immatriculation_coherence", # C-07 — Immat CG ↔ Cerfa ↔ CT ↔ cession
    ],
)

IdentiteCoherenceValidator = CoherenceMetaValidator(
    v_code="V-25",
    v_message="Identité incohérente entre documents",
    watched_rules=[
        "name_cni_facture_nom",         # C-01 — CNI ↔ Facture
        "name_cni_permis_nom",          # C-03 — CNI ↔ Permis
        "name_cni_permis_prenom",       # C-03
        "ddn_cni_permis",              # C-03 — DDN CNI ↔ Permis
        "name_cni_assurance_nom",       # C-01 — CNI ↔ Assurance
        "name_cni_domicile_nom",        # C-01 — CNI ↔ Domicile
        "address_cerfa_vs_domicile",    # C-04 — Adresse Cerfa ↔ Domicile
        "address_cerfa_vs_titre_sejour",# C-05 — Adresse Cerfa ↔ Titre séjour
    ],
)

ChaineProprieteValidator = CoherenceMetaValidator(
    v_code="V-26",
    v_message="Chaîne de propriété brisée",
    watched_rules=[
        "vendeur_da_vs_titulaire_cg",  # C-11 — Vendeur DA = titulaire CG
        "siret_cession_vs_da",         # C-11 — SIRET cession ↔ DA
        "cg_date_vs_da_date",          # C-12 — Dates
        "da_date_vs_cession_date",     # C-12
        "recepisse_da_delay",          # C-12 — Récépissé DA < 15j
        "cg_signatures_vs_cotitulaires",# C-13 — Signatures
        "cession_signature_vendeur",   # C-13
    ],
)

PermisCategorieValidator = CoherenceMetaValidator(
    v_code="V-27",
    v_message="Catégorie de permis incompatible avec le véhicule",
    watched_rules=[
        "permis_categorie_vehicule",   # C-15 — Permis ↔ type véhicule
    ],
)

AgeCompatibiliteValidator = CoherenceMetaValidator(
    v_code="V-28",
    v_message="Âge de l'acheteur incompatible avec la catégorie du véhicule",
    watched_rules=[
        "age_categorie_vehicule",      # C-16 — Âge ↔ catégorie
    ],
)
