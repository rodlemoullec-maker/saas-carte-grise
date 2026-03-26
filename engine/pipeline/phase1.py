"""
Pipeline Phase 1 — Pré-qualification complète du dossier.

Enchaîne toutes les étapes de vérification automatique :
  1. Complétude documentaire (V-01 → V-10, V-36)
  2. Qualité / lisibilité (V-20, V-21, V-22)
  3. Extraction OCR par document
  4. Validation individuelle par type (dates, VIN, SIRET, etc.)
  5. Cross-checks inter-documents (C-01 → C-21)
  6. Méta-validateurs de cohérence (V-24 → V-28)
  7. Scoring global
  8. Décision + diagnostic VERT / ORANGE / ROUGE
  9. Estimation indicative des taxes

Entrée  : Dossier avec documents uploadés
Sortie  : Phase1Result (diagnostic, score, issues, estimation taxes)
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from enum import Enum
from typing import Any

from engine.cross_checks.address_checks import (
    AddressCerfaDomicileCheck,
    AddressCerfaTitreSejourCheck,
)
from engine.cross_checks.coc_cerfa_checks import (
    CNITUTACCheck,
    CO2WLTPCheck,
    PuissanceFiscaleCheck,
)
from engine.cross_checks.identity_consistency import IdentityConsistencyCheck
from engine.cross_checks.vehicle_coherence import VehicleCoherenceCheck
from engine.cross_checks.vin_consistency import VINConsistencyCheck
from engine.cross_checks.vo_checks import (
    ChaineProprieteCheck,
    CTSaisieCheck,
    DatesCGBarreeCheck,
    SignaturesCotitulaireCheck,
)
from engine.decision.engine import DecisionEngine
from engine.decision.scoring import compute_score
from engine.models.decision import CrossCheckResult, CrossCheckStatus, Decision, DecisionStatus
from engine.models.documents import (
    DocumentType,
    ExtractedAssurance,
    ExtractedCerfa,
    ExtractedCGBarree,
    ExtractedCession,
    ExtractedCOC,
    ExtractedCT,
    ExtractedDA,
    ExtractedDomicile,
    ExtractedFacture,
    ExtractedIdentite,
    ExtractedPermis,
    ExtractedRecepisseDA,
)
from engine.validators.coherence_meta import (
    AgeCompatibiliteValidator,
    ChaineProprieteValidator,
    IdentiteCoherenceValidator,
    PermisCategorieValidator,
    VINCoherenceValidator,
)
from engine.validators.completeness import (
    CompletenessValidator,
    DossierDocuments,
    FlowType,
)
from engine.validators.documents import (
    AssuranceDocumentValidator,
    AttestationIdentiteProValidator,
    CerfaValidator,
    CGBarreeValidator,
    COCDocumentValidator,
    CTDocumentValidator,
    DomicileDocumentValidator,
    FactureDocumentValidator,
    IdentiteDocumentValidator,
    PermisDocumentValidator,
)
from engine.validators.quality import DocumentQualityMetadata, DocumentQualityValidator


class Diagnostic(str, Enum):
    VERT = "VERT"       # Tous les checks passent — prêt pour GO/NO-GO
    ORANGE = "ORANGE"   # Warnings — le pro peut continuer mais doit vérifier
    ROUGE = "ROUGE"     # Blocages — corrections requises avant de continuer


@dataclass
class Phase1Result:
    diagnostic: Diagnostic
    score: float
    decision: Decision
    cross_check_results: list[CrossCheckResult] = field(default_factory=list)
    validation_errors: list[dict[str, Any]] = field(default_factory=list)
    validation_warnings: list[dict[str, Any]] = field(default_factory=list)
    completeness_errors: list[dict[str, Any]] = field(default_factory=list)
    quality_errors: list[dict[str, Any]] = field(default_factory=list)
    tax_estimate: dict[str, Any] | None = None


@dataclass
class ExtractedDocuments:
    """Container pour tous les documents extraits d'un dossier."""
    flow_type: FlowType = FlowType.VN

    # Identité
    identite: ExtractedIdentite | None = None
    permis: ExtractedPermis | None = None
    domicile: ExtractedDomicile | None = None

    # Véhicule VN
    coc: ExtractedCOC | None = None
    facture: ExtractedFacture | None = None

    # Véhicule VO
    cg_barree: ExtractedCGBarree | None = None
    ct: ExtractedCT | None = None
    da: ExtractedDA | None = None
    recepisse_da: ExtractedRecepisseDA | None = None
    cession: ExtractedCession | None = None

    # Commun
    cerfa: ExtractedCerfa | None = None
    assurance: ExtractedAssurance | None = None

    # Métadonnées
    attestation_identite_pro: bool = False
    is_personne_morale: bool = False
    is_mineur: bool = False
    is_etranger: bool = False
    ct_dispense: bool = False
    ct_volontaire: bool = False
    pro_habilite_siv: bool = False
    cg_perdue: bool = False

    # Qualité docs (par type de doc)
    quality_metadata: dict[str, DocumentQualityMetadata] = field(default_factory=dict)


class Phase1Pipeline:
    """
    Orchestre la pré-qualification Phase 1 d'un dossier.

    Usage typique (dans un worker Celery) :
        extracted = await extract_all_documents(dossier)
        result = Phase1Pipeline().run(extracted)
        update_dossier_status(dossier.id, result)
    """

    def run(
        self,
        docs: ExtractedDocuments,
        reference_date: date | None = None,
        saisie_siv_date: date | None = None,
    ) -> Phase1Result:
        ref = reference_date or date.today()
        all_cross_checks: list[CrossCheckResult] = []
        all_errors: list[dict] = []
        all_warnings: list[dict] = []
        completeness_errors: list[dict] = []
        quality_errors: list[dict] = []

        # ──── ETAPE 1 : Complétude ────────────────────────────────────────
        completeness_result = self._check_completeness(docs)
        for err in completeness_result.errors:
            completeness_errors.append({
                "code": err.code, "message": err.message,
                "level": err.level.value, "field": err.field,
                "correction": err.correction_action,
            })
        for w in completeness_result.warnings:
            all_warnings.append({
                "code": w.code, "message": w.message,
                "level": "WARNING", "field": w.field,
            })

        # ──── ETAPE 2 : Qualité documentaire ──────────────────────────────
        quality_validator = DocumentQualityValidator()
        for doc_type, quality in docs.quality_metadata.items():
            q_result = quality_validator.validate(quality)
            for err in q_result.errors:
                quality_errors.append({
                    "code": err.code, "message": err.message,
                    "level": err.level.value, "document": doc_type,
                    "correction": err.correction_action,
                })
            for w in q_result.warnings:
                all_warnings.append({
                    "code": w.code, "message": w.message,
                    "level": "WARNING", "document": doc_type,
                })

        # ──── ETAPE 3 : Validation individuelle par document ──────────────
        self._validate_individual_documents(docs, ref, all_errors, all_warnings)

        # ──── ETAPE 4 : Cross-checks inter-documents ─────────────────────
        self._run_cross_checks(docs, ref, saisie_siv_date, all_cross_checks)

        # ──── ETAPE 5 : Méta-validateurs V-24→V-28 ───────────────────────
        for meta_validator in [
            VINCoherenceValidator,
            IdentiteCoherenceValidator,
            ChaineProprieteValidator,
            PermisCategorieValidator,
            AgeCompatibiliteValidator,
        ]:
            meta_result = meta_validator.validate(all_cross_checks)
            for err in meta_result.errors:
                all_errors.append({
                    "code": err.code, "message": err.message,
                    "level": err.level.value, "field": err.field,
                })
            for w in meta_result.warnings:
                all_warnings.append({
                    "code": w.code, "message": w.message,
                    "level": "WARNING", "field": w.field,
                })

        # ──── ETAPE 6 : Scoring global ───────────────────────────────────
        score = compute_score(all_cross_checks)

        # ──── ETAPE 7 : Décision ─────────────────────────────────────────
        decision = DecisionEngine().decide(all_cross_checks)

        # ──── ETAPE 8 : Estimation taxes ─────────────────────────────────
        tax_estimate = self._estimate_taxes(docs)

        # ──── ETAPE 9 : Diagnostic ───────────────────────────────────────
        has_blocking = (
            completeness_result.is_blocking
            or any(e["level"] == "BLOCKING" for e in all_errors)
            or any(e["level"] == "BLOCKING" for e in quality_errors)
            or decision.status in (DecisionStatus.REJET, DecisionStatus.FRAUDE)
        )
        has_warnings = (
            len(all_warnings) > 0
            or decision.status == DecisionStatus.REVUE_AGENT
        )

        if has_blocking:
            diagnostic = Diagnostic.ROUGE
        elif has_warnings:
            diagnostic = Diagnostic.ORANGE
        else:
            diagnostic = Diagnostic.VERT

        return Phase1Result(
            diagnostic=diagnostic,
            score=score,
            decision=decision,
            cross_check_results=all_cross_checks,
            validation_errors=all_errors,
            validation_warnings=all_warnings,
            completeness_errors=completeness_errors,
            quality_errors=quality_errors,
            tax_estimate=tax_estimate,
        )

    # ──── Helpers privés ──────────────────────────────────────────────────

    def _check_completeness(self, docs: ExtractedDocuments):
        dossier_docs = DossierDocuments(
            cni_ou_passeport=docs.identite is not None,
            permis=docs.permis is not None,
            justif_domicile=docs.domicile is not None,
            cerfa_cg=docs.cerfa is not None,
            mandat=True,  # TODO: vérifier si mandat fourni
            cerfa_cession=docs.cession is not None,
            coc=docs.coc is not None,
            cg_barree=docs.cg_barree is not None,
            controle_technique=docs.ct is not None,
            assurance=docs.assurance is not None,
            da=docs.da is not None,
            recepisse_da=docs.recepisse_da is not None,
            attestation_identite_pro=docs.attestation_identite_pro,
            is_personne_morale=docs.is_personne_morale,
            is_mineur=docs.is_mineur,
            is_etranger=docs.is_etranger,
            ct_dispense=docs.ct_dispense,
            ct_volontaire=docs.ct_volontaire,
            pro_habilite_siv=docs.pro_habilite_siv,
            cg_perdue=docs.cg_perdue,
        )
        return CompletenessValidator().validate(docs.flow_type, dossier_docs)

    def _validate_individual_documents(self, docs, ref, errors, warnings):
        """Valide chaque document individuellement."""

        def _collect(result):
            for err in result.errors:
                errors.append({
                    "code": err.code, "message": err.message,
                    "level": err.level.value, "field": err.field,
                    "correction": err.correction_action,
                })
            for w in result.warnings:
                warnings.append({
                    "code": w.code, "message": w.message,
                    "level": "WARNING", "field": w.field,
                })

        if docs.identite:
            _collect(IdentiteDocumentValidator().validate(docs.identite, ref))

        if docs.permis:
            vehicle_type = None
            if docs.coc and docs.coc.carrosserie:
                vehicle_type = docs.coc.carrosserie
            _collect(PermisDocumentValidator().validate(docs.permis, vehicle_type, ref))

        if docs.domicile:
            _collect(DomicileDocumentValidator().validate(docs.domicile, ref))

        if docs.coc:
            _collect(COCDocumentValidator().validate(docs.coc, ref))

        if docs.facture:
            _collect(FactureDocumentValidator().validate(docs.facture, ref))

        if docs.assurance:
            _collect(AssuranceDocumentValidator().validate(docs.assurance, ref))

        if docs.cerfa:
            _collect(CerfaValidator().validate(docs.cerfa))

        # VO-specific
        if docs.cg_barree:
            _collect(CGBarreeValidator().validate(docs.cg_barree))

        if docs.ct:
            _collect(CTDocumentValidator().validate(docs.ct, saisie_siv_date=None))

        if not docs.attestation_identite_pro:
            _collect(AttestationIdentiteProValidator().validate(False))

    def _run_cross_checks(self, docs, ref, saisie_siv_date, results):
        """Exécute tous les cross-checks applicables."""

        # VIN consistency (VN : COC ↔ Facture ↔ Assurance)
        if docs.coc and docs.facture:
            results.extend(
                VINConsistencyCheck().run(docs.coc, docs.facture, docs.assurance)
            )

        # Vehicle coherence (VN : COC ↔ Facture)
        if docs.coc and docs.facture:
            results.extend(
                VehicleCoherenceCheck().run(docs.coc, docs.facture)
            )

        # Identity consistency
        if docs.identite and docs.facture and docs.permis and docs.domicile and docs.assurance:
            results.extend(
                IdentityConsistencyCheck().run(
                    docs.identite, docs.facture, docs.permis, docs.domicile, docs.assurance,
                )
            )

        # Address checks
        if docs.cerfa and docs.domicile:
            results.extend(
                AddressCerfaDomicileCheck().run(docs.cerfa, docs.domicile)
            )

        if docs.cerfa and docs.identite:
            results.extend(
                AddressCerfaTitreSejourCheck().run(docs.cerfa, docs.identite)
            )

        # COC / Cerfa technique
        if docs.coc:
            results.extend(CNITUTACCheck().run(docs.coc))
            results.extend(CO2WLTPCheck().run(docs.coc))

        if docs.coc and docs.cerfa:
            results.extend(
                PuissanceFiscaleCheck().run(docs.coc, docs.cerfa)
            )

        # VO cross-checks
        if docs.cg_barree and docs.da:
            results.extend(
                ChaineProprieteCheck().run(docs.cg_barree, docs.da, docs.cession)
            )
            results.extend(
                DatesCGBarreeCheck().run(
                    docs.cg_barree, docs.da, docs.cession, docs.recepisse_da,
                )
            )

        if docs.cg_barree:
            results.extend(
                SignaturesCotitulaireCheck().run(docs.cg_barree, docs.cession)
            )

        if docs.ct and docs.ct.date_ct:
            results.extend(
                CTSaisieCheck().run(docs.ct.date_ct, saisie_siv_date)
            )

    def _estimate_taxes(self, docs: ExtractedDocuments) -> dict[str, Any] | None:
        """Calcule une estimation indicative des taxes (non contractuelle)."""
        try:
            from engine.taxes.calculator import TaxCalculator
            return TaxCalculator().estimate(docs)
        except Exception:
            return None
