"""
Croisements cohérence véhicule — COC vs Facture.
"""
from __future__ import annotations

from engine.cross_checks.base import BaseCrossCheck
from engine.models.decision import CrossCheckResult, CrossCheckStatus
from engine.models.documents import ExtractedCOC, ExtractedFacture
from engine.normalizers.vehicles import energies_match, normalize_marque


class VehicleCoherenceCheck(BaseCrossCheck):

    @property
    def name(self) -> str:
        return "vehicle_coherence"

    def run(self, coc: ExtractedCOC, facture: ExtractedFacture) -> list[CrossCheckResult]:
        results = []

        # Marque
        marque_coc = normalize_marque(coc.marque)
        marque_facture = normalize_marque(facture.marque)
        if marque_coc == marque_facture:
            results.append(CrossCheckResult(
                rule_name="marque_coc_facture",
                status=CrossCheckStatus.PASS,
                source_a="COC", source_b="FACTURE",
                field="marque",
                value_a=marque_coc, value_b=marque_facture,
                confidence=1.0,
            ))
        else:
            results.append(CrossCheckResult(
                rule_name="marque_coc_facture",
                status=CrossCheckStatus.FAIL,
                source_a="COC", source_b="FACTURE",
                field="marque",
                value_a=marque_coc, value_b=marque_facture,
                confidence=0.0,
                detail=f"Marque différente : COC='{marque_coc}' vs Facture='{marque_facture}'",
            ))

        # Énergie (si présente sur facture)
        if facture.energie:
            if energies_match(coc.energie, facture.energie):
                results.append(CrossCheckResult(
                    rule_name="energie_coc_facture",
                    status=CrossCheckStatus.PASS,
                    source_a="COC", source_b="FACTURE",
                    field="energie",
                    value_a=coc.energie, value_b=facture.energie,
                    confidence=1.0,
                ))
            else:
                results.append(CrossCheckResult(
                    rule_name="energie_coc_facture",
                    status=CrossCheckStatus.FAIL,
                    source_a="COC", source_b="FACTURE",
                    field="energie",
                    value_a=coc.energie, value_b=facture.energie,
                    confidence=0.0,
                    detail=f"Énergie incohérente : COC='{coc.energie}' vs Facture='{facture.energie}'",
                ))

        # Puissance kW — tolérance ±5%
        if coc.puissance_kw and facture.prix_ttc:  # proxy : si facture a données techniques
            pass  # TODO: comparer si facture mentionne la puissance

        return results
