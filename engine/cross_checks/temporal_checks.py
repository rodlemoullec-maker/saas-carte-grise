"""
Vérifications de cohérence temporelle entre documents.
"""
from __future__ import annotations

from datetime import date

from engine.cross_checks.base import BaseCrossCheck
from engine.models.decision import CrossCheckResult, CrossCheckStatus
from engine.models.documents import ExtractedAssurance, ExtractedFacture


class TemporalCoherenceCheck(BaseCrossCheck):

    @property
    def name(self) -> str:
        return "temporal_coherence"

    def run(
        self,
        facture: ExtractedFacture,
        assurance: ExtractedAssurance,
        reference_date: date | None = None,
    ) -> list[CrossCheckResult]:
        results = []
        ref = reference_date or date.today()

        # Facture antérieure ou égale à aujourd'hui
        if facture.date_vente <= ref:
            results.append(CrossCheckResult(
                rule_name="facture_date_vs_today",
                status=CrossCheckStatus.PASS,
                source_a="FACTURE", source_b="SYSTEM",
                field="date_vente",
                value_a=str(facture.date_vente), value_b=str(ref),
                confidence=1.0,
            ))
        else:
            results.append(CrossCheckResult(
                rule_name="facture_date_vs_today",
                status=CrossCheckStatus.FAIL,
                source_a="FACTURE", source_b="SYSTEM",
                field="date_vente",
                value_a=str(facture.date_vente), value_b=str(ref),
                confidence=0.0,
                detail="Date de vente dans le futur",
            ))

        # Assurance active à la date de demande
        if assurance.date_effet <= ref <= assurance.date_echeance:
            results.append(CrossCheckResult(
                rule_name="assurance_active_today",
                status=CrossCheckStatus.PASS,
                source_a="ASSURANCE", source_b="SYSTEM",
                field="periode",
                value_a=f"{assurance.date_effet}→{assurance.date_echeance}",
                value_b=str(ref),
                confidence=1.0,
            ))
        else:
            results.append(CrossCheckResult(
                rule_name="assurance_active_today",
                status=CrossCheckStatus.FAIL,
                source_a="ASSURANCE", source_b="SYSTEM",
                field="periode",
                value_a=f"{assurance.date_effet}→{assurance.date_echeance}",
                value_b=str(ref),
                confidence=0.0,
                detail="Assurance non active à la date de la demande",
            ))

        # Assurance souscrite dans un délai raisonnable après la vente (< 30j)
        delta_assurance = (assurance.date_effet - facture.date_vente).days
        if delta_assurance > 30:
            results.append(CrossCheckResult(
                rule_name="assurance_delay_after_sale",
                status=CrossCheckStatus.WARNING,
                source_a="FACTURE", source_b="ASSURANCE",
                field="date_effet",
                value_a=str(factura.date_vente), value_b=str(assurance.date_effet),
                confidence=0.8,
                detail=f"Assurance souscrite {delta_assurance} jours après la vente (> 30j)",
            ))

        return results
