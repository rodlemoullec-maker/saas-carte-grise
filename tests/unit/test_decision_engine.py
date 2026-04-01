"""Tests unitaires — DecisionEngine (logique binaire, pas de score)."""
from __future__ import annotations
from engine.decision.engine import DecisionEngine
from engine.models.decision import CrossCheckResult, CrossCheckStatus, DecisionStatus, Diagnostic


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

    def test_fraud_rule_gives_fraude(self):
        results = self._make_results({"vin_coc_facture": CrossCheckStatus.FAIL})
        decision = self.engine.decide(results, [], extra_blocking_rules=["vin_coc_facture_mismatch"])
        assert decision.status == DecisionStatus.FRAUDE
        assert decision.diagnostic == Diagnostic.ROUGE

    def test_non_fraud_blocking_gives_correction(self):
        results = self._make_results({"vin_coc_facture": CrossCheckStatus.PASS})
        decision = self.engine.decide(results, [], extra_blocking_rules=["missing_mandatory_document"])
        assert decision.status == DecisionStatus.CORRECTION
        assert decision.diagnostic == Diagnostic.ROUGE
        assert "missing_mandatory_document" in decision.blocages

    def test_all_pass_gives_vert(self):
        results = self._make_results({
            "vin_coc_facture": CrossCheckStatus.PASS,
            "vin_coc_assurance": CrossCheckStatus.PASS,
            "marque_coc_facture": CrossCheckStatus.PASS,
            "name_cni_facture_nom": CrossCheckStatus.PASS,
            "name_cni_permis_nom": CrossCheckStatus.PASS,
            "ddn_cni_permis": CrossCheckStatus.PASS,
        })
        decision = self.engine.decide(results, [])
        assert decision.status == DecisionStatus.ACCEPTE
        assert decision.diagnostic == Diagnostic.VERT
        assert len(decision.blocages) == 0
        assert len(decision.warnings) == 0

    def test_warning_gives_orange(self):
        results = [
            CrossCheckResult(
                rule_name="assurance_delay_after_sale",
                status=CrossCheckStatus.WARNING,
                source_a="ASSURANCE", source_b="SYSTEM", field="date_effet",
                detail="Assurance souscrite 20 jours apres la vente",
            ),
        ]
        decision = self.engine.decide(results, [])
        assert decision.diagnostic == Diagnostic.ORANGE
        assert decision.status == DecisionStatus.REVUE_AGENT
        assert len(decision.warnings) > 0

    def test_no_results_gives_vert(self):
        decision = self.engine.decide([], [])
        assert decision.diagnostic == Diagnostic.VERT
        assert decision.status == DecisionStatus.ACCEPTE
