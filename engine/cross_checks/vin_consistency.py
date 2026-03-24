"""
Croisements VIN inter-documents.

Règles :
- VIN COC = VIN Facture (strict, bloquant)
- VIN COC = VIN Assurance (si présent sur assurance)
- WMI (3 premiers chars) cohérent avec constructeur déclaré dans COC
"""
from __future__ import annotations

from engine.cross_checks.base import BaseCrossCheck
from engine.models.decision import CrossCheckResult, CrossCheckStatus
from engine.models.documents import ExtractedAssurance, ExtractedCOC, ExtractedFacture


class VINConsistencyCheck(BaseCrossCheck):

    @property
    def name(self) -> str:
        return "vin_consistency"

    def run(
        self,
        coc: ExtractedCOC,
        facture: ExtractedFacture,
        assurance: ExtractedAssurance | None = None,
    ) -> list[CrossCheckResult]:
        results = []

        # COC vs Facture — BLOQUANT
        vin_coc = coc.vin.upper().replace(" ", "").replace("-", "")
        vin_facture = facture.vin.upper().replace(" ", "").replace("-", "")

        if vin_coc == vin_facture:
            results.append(CrossCheckResult(
                rule_name="vin_coc_facture",
                status=CrossCheckStatus.PASS,
                source_a="COC", source_b="FACTURE",
                field="vin",
                value_a=vin_coc, value_b=vin_facture,
                confidence=1.0,
            ))
        else:
            results.append(CrossCheckResult(
                rule_name="vin_coc_facture",
                status=CrossCheckStatus.FAIL,
                source_a="COC", source_b="FACTURE",
                field="vin",
                value_a=vin_coc, value_b=vin_facture,
                confidence=0.0,
                detail=f"VIN COC ({vin_coc}) ≠ VIN Facture ({vin_facture}) — BLOQUANT",
            ))

        # COC vs Assurance (optionnel si assurance provisoire)
        if assurance and assurance.vin:
            vin_assurance = assurance.vin.upper().replace(" ", "").replace("-", "")
            if vin_coc == vin_assurance:
                results.append(CrossCheckResult(
                    rule_name="vin_coc_assurance",
                    status=CrossCheckStatus.PASS,
                    source_a="COC", source_b="ASSURANCE",
                    field="vin",
                    value_a=vin_coc, value_b=vin_assurance,
                    confidence=1.0,
                ))
            else:
                results.append(CrossCheckResult(
                    rule_name="vin_coc_assurance",
                    status=CrossCheckStatus.FAIL,
                    source_a="COC", source_b="ASSURANCE",
                    field="vin",
                    value_a=vin_coc, value_b=vin_assurance,
                    confidence=0.0,
                    detail=f"VIN COC ({vin_coc}) ≠ VIN Assurance ({vin_assurance})",
                ))
        elif assurance and not assurance.vin:
            results.append(CrossCheckResult(
                rule_name="vin_coc_assurance",
                status=CrossCheckStatus.WARNING,
                source_a="COC", source_b="ASSURANCE",
                field="vin",
                value_a=vin_coc, value_b=None,
                confidence=0.7,
                detail="VIN absent sur assurance (provisoire) — vérifier marque/modèle",
            ))

        # WMI check (les 3 premiers caractères identifient le constructeur)
        # TODO: vérifier WMI contre base NHTSA/OICA
        # wmi = vin_coc[:3]
        # manufacturer = lookup_wmi(wmi)
        # if manufacturer and not marques_match(manufacturer, coc.constructeur):
        #     results.append(FAIL fraud alert)

        return results
