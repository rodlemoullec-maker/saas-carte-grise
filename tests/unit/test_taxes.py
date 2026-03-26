"""Tests unitaires — TaxCalculator."""
from __future__ import annotations

from datetime import date

import pytest

from engine.pipeline.phase1 import ExtractedDocuments
from engine.models.documents import ExtractedCOC, ExtractedCerfa, ExtractedDomicile
from engine.taxes.calculator import TaxCalculator
from engine.validators.completeness import FlowType


class TestTaxCalculator:

    def setup_method(self):
        self.calc = TaxCalculator()

    def _make_docs(self, **coc_overrides) -> ExtractedDocuments:
        coc_defaults = dict(
            vin="X", marque="RENAULT", energie="Essence",
            puissance_fiscale_cv=7, co2_wltp=130.0,
        )
        coc_defaults.update(coc_overrides)
        return ExtractedDocuments(
            flow_type=FlowType.VN,
            coc=ExtractedCOC(**coc_defaults),
            cerfa=ExtractedCerfa(code_postal="75002"),
            domicile=ExtractedDomicile(
                nom_titulaire="DUPONT", adresse_ligne1="X", code_postal="75002",
                ville="Paris", date_document=date(2026, 1, 1),
            ),
        )

    def test_basic_estimation(self):
        docs = self._make_docs()
        result = self.calc.estimate(docs)
        assert result["total"] > 0
        assert result["is_estimate"] is True

    def test_taxe_regionale_paris(self):
        docs = self._make_docs(puissance_fiscale_cv=7)
        result = self.calc.estimate(docs)
        # Paris = 46.15€/CV × 7 = 323.05€
        assert result["y1_taxe_regionale"] == pytest.approx(46.15 * 7, rel=0.01)

    def test_electrique_exonere(self):
        docs = self._make_docs(energie="Electrique", co2_wltp=None)
        result = self.calc.estimate(docs)
        assert result["y1_taxe_regionale"] == 0.0
        assert result["y3_malus_co2"] == 0.0
        assert result["y4_taxe_gestion"] == 0.0

    def test_malus_co2_above_threshold(self):
        docs = self._make_docs(co2_wltp=180.0)
        result = self.calc.estimate(docs)
        assert result["y3_malus_co2"] > 0

    def test_no_malus_below_threshold(self):
        docs = self._make_docs(co2_wltp=100.0)
        result = self.calc.estimate(docs)
        assert result["y3_malus_co2"] == 0

    def test_malus_poids(self):
        docs = self._make_docs(ptac_kg=2200)
        result = self.calc.estimate(docs)
        # (2200 - 1800) × 10 = 4000€
        assert result["y6_malus_poids"] == 4000.0

    def test_redevance_always_present(self):
        docs = self._make_docs()
        result = self.calc.estimate(docs)
        assert result["y5_redevance"] == 2.76

    def test_notes_always_present(self):
        docs = self._make_docs()
        result = self.calc.estimate(docs)
        assert len(result["notes"]) > 0
        assert any("INDICATIVE" in n or "indicatif" in n.lower() for n in result["notes"])
