"""Tests unitaires — DecisionEngine."""
from __future__ import annotations
from engine.decision.engine import DecisionEngine
from engine.models.decision import CrossCheckResult, CrossCheckStatus, DecisionStatus


class TestDecisionEngine:

    def setup_method(self):
        self.engine = DecisionEngine()

    def _make_results(self, statuses: dict[str, CrossCheckStatus]) -> list[CrossCheckResult]:
        return [
            CrossCheckResult(
                rule_name=rule, status=status,
                source_a="A", source_b="B", field="f",
            )
            for rule, status in statuses.items()
        ]

    def test_blocking_rule_forces_rejet(self):
        results = self._make_results({"vin_coc_facture": CrossCheckStatus.FAIL})
        decision = self.engine.decide(results, [], extra_blocking_rules=["vin_coc_facture_mismatch"])
        assert decision.status == DecisionStatus.REJET

    def test_all_pass_gives_accepte(self):
        results = self._make_results({
            "vin_coc_facture": CrossCheckStatus.PASS,
            "vin_coc_assurance": CrossCheckStatus.PASS,
            "marque_coc_facture": CrossCheckStatus.PASS,
            "energie_coc_facture": CrossCheckStatus.PASS,
            "name_cni_facture_nom": CrossCheckStatus.PASS,
            "name_cni_permis_nom": CrossCheckStatus.PASS,
            "ddn_cni_permis": CrossCheckStatus.PASS,
            "name_cni_assurance_nom": CrossCheckStatus.PASS,
            "name_cni_domicile_nom": CrossCheckStatus.PASS,
            "facture_date_vs_today": CrossCheckStatus.PASS,
            "assurance_active_today": CrossCheckStatus.PASS,
        })
        decision = self.engine.decide(results, [])
        assert decision.status == DecisionStatus.ACCEPTE
        assert decision.score >= 95.0
