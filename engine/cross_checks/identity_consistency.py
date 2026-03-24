"""
Croisements identité inter-documents.

Compare le nom/prénom/DDN de la CNI avec la facture, le permis, l'assurance
et le justificatif de domicile.
"""
from __future__ import annotations

from engine.cross_checks.base import BaseCrossCheck
from engine.models.decision import CrossCheckResult, CrossCheckStatus
from engine.models.documents import (
    ExtractedAssurance,
    ExtractedDomicile,
    ExtractedFacture,
    ExtractedIdentite,
    ExtractedPermis,
)
from engine.normalizers.names import match_names


class IdentityConsistencyCheck(BaseCrossCheck):

    @property
    def name(self) -> str:
        return "identity_consistency"

    def run(
        self,
        identite: ExtractedIdentite,
        facture: ExtractedFacture,
        permis: ExtractedPermis,
        domicile: ExtractedDomicile,
        assurance: ExtractedAssurance,
    ) -> list[CrossCheckResult]:
        results = []
        nom_ref = identite.nom_naissance
        prenom_ref = identite.prenoms[0] if identite.prenoms else ""

        # CNI vs Facture — Nom
        results.append(self._check_name(nom_ref, facture.nom_acheteur,
                                        "CNI", "FACTURE", "nom"))

        # CNI vs Permis — Nom + Prénom + DDN
        results.append(self._check_name(nom_ref, permis.nom, "CNI", "PERMIS", "nom"))
        results.append(self._check_name(prenom_ref, permis.prenom, "CNI", "PERMIS", "prenom"))

        if identite.date_naissance != permis.date_naissance:
            results.append(CrossCheckResult(
                rule_name="ddn_cni_permis",
                status=CrossCheckStatus.FAIL,
                source_a="CNI", source_b="PERMIS",
                field="date_naissance",
                value_a=str(identite.date_naissance),
                value_b=str(permis.date_naissance),
                confidence=0.0,
                detail="Date de naissance différente entre CNI et permis — BLOQUANT",
            ))
        else:
            results.append(CrossCheckResult(
                rule_name="ddn_cni_permis",
                status=CrossCheckStatus.PASS,
                source_a="CNI", source_b="PERMIS",
                field="date_naissance",
                value_a=str(identite.date_naissance),
                value_b=str(permis.date_naissance),
                confidence=1.0,
            ))

        # CNI vs Assurance — Nom (tolérance nom d'usage)
        results.append(self._check_name(nom_ref, assurance.nom_assure,
                                        "CNI", "ASSURANCE", "nom", tolerance_usage=True))

        # CNI vs Domicile — Nom
        results.append(self._check_name(nom_ref, domicile.nom_titulaire,
                                        "CNI", "DOMICILE", "nom", tolerance_usage=True))

        return results

    def _check_name(
        self,
        name_ref: str,
        name_target: str,
        source_a: str,
        source_b: str,
        field: str,
        tolerance_usage: bool = False,
    ) -> CrossCheckResult:
        match_result = match_names(name_ref, name_target)
        rule_name = f"name_{source_a.lower()}_{source_b.lower()}_{field}"

        if match_result.matched and match_result.confidence >= 0.97:
            status = CrossCheckStatus.PASS
        elif match_result.matched and match_result.confidence >= 0.85:
            status = CrossCheckStatus.WARNING
        else:
            status = CrossCheckStatus.FAIL

        return CrossCheckResult(
            rule_name=rule_name,
            status=status,
            source_a=source_a,
            source_b=source_b,
            field=field,
            value_a=name_ref,
            value_b=name_target,
            confidence=match_result.confidence,
            detail=match_result.note,
        )
