"""Tests unitaires — Pipeline Phase 0 + Phase 1."""
from __future__ import annotations

from datetime import date

import pytest

from engine.models.documents import (
    ExtractedAssurance,
    ExtractedCerfa,
    ExtractedCOC,
    ExtractedDomicile,
    ExtractedFacture,
    ExtractedHistoVec,
    ExtractedIdentite,
    ExtractedPermis,
    PermisCategorie,
)
from engine.pipeline.phase0 import Phase0Pipeline, Phase0Verdict
from engine.models.decision import Diagnostic
from engine.pipeline.phase1 import ExtractedDocuments, Phase1Pipeline
from engine.validators.completeness import FlowType


class TestPhase0Pipeline:

    def test_clean_vehicle(self):
        h = ExtractedHistoVec(immatriculation="AA-123-BB", gage_actif=False, otci_active=False, vol_signale=False, vec=False, vei=False)
        result = Phase0Pipeline().run(h)
        assert result.verdict == Phase0Verdict.GO
        assert len(result.blockers) == 0

    def test_gage_blocks(self):
        h = ExtractedHistoVec(immatriculation="AA-123-BB", gage_actif=True, otci_active=False, vol_signale=False, vec=False, vei=False)
        result = Phase0Pipeline().run(h)
        assert result.verdict == Phase0Verdict.STOP
        assert len(result.blockers) > 0

    def test_vol_blocks(self):
        h = ExtractedHistoVec(immatriculation="AA-123-BB", gage_actif=False, otci_active=False, vol_signale=True, vec=False, vei=False)
        result = Phase0Pipeline().run(h)
        assert result.verdict == Phase0Verdict.STOP

    def test_otci_blocks(self):
        h = ExtractedHistoVec(immatriculation="AA-123-BB", gage_actif=False, otci_active=True, vol_signale=False, vec=False, vei=False)
        result = Phase0Pipeline().run(h)
        assert result.verdict == Phase0Verdict.STOP

    def test_vec_warning(self):
        h = ExtractedHistoVec(immatriculation="AA-123-BB", gage_actif=False, otci_active=False, vol_signale=False, vec=True, vei=False)
        result = Phase0Pipeline().run(h)
        assert result.verdict == Phase0Verdict.WARNING
        assert len(result.warnings) > 0

    def test_vei_blocks(self):
        h = ExtractedHistoVec(immatriculation="AA-123-BB", gage_actif=False, otci_active=False, vol_signale=False, vec=False, vei=True)
        result = Phase0Pipeline().run(h)
        assert result.verdict == Phase0Verdict.STOP

    def test_km_reported(self):
        h = ExtractedHistoVec(
            immatriculation="AA-123-BB",
            gage_actif=False, otci_active=False, vol_signale=False,
            vec=False, vei=False, km_dernier_ct=85000,
        )
        result = Phase0Pipeline().run(h)
        assert result.verdict == Phase0Verdict.WARNING
        assert any("85" in w for w in result.warnings)


class TestPhase1Pipeline:

    def _make_docs_vn(self) -> ExtractedDocuments:
        """Crée un jeu de documents VN complet et valide."""
        return ExtractedDocuments(
            flow_type=FlowType.VN,
            identite=ExtractedIdentite(
                nom_naissance="DUPONT",
                prenoms=["Jean"],
                date_naissance=date(1990, 5, 15),
                date_expiration=date(2030, 1, 1),
                n_document="ABC123456",
                type_document="CNI",
            ),
            permis=ExtractedPermis(
                nom="DUPONT",
                prenom="Jean",
                date_naissance=date(1990, 5, 15),
                n_permis="12AB34567",
                categories=[PermisCategorie(code="B", date_obtention=date(2010, 1, 1))],
            ),
            domicile=ExtractedDomicile(
                nom_titulaire="DUPONT",
                adresse_ligne1="12 rue de la Paix",
                code_postal="75002",
                ville="Paris",
                date_document=date(2026, 2, 1),
            ),
            coc=ExtractedCOC(
                vin="VF1RFD00068123456",
                marque="RENAULT",
                energie="Essence",
                puissance_fiscale_cv=7,
                co2_wltp=130.0,
                cnit="AB12345C",
            ),
            facture=ExtractedFacture(
                vin="VF1RFD00068123456",
                marque="RENAULT",
                nom_vendeur="GARAGE DUPLEX",
                nom_acheteur="DUPONT",
                siret_vendeur="73282932000074",
                date_vente=date(2026, 3, 15),
                prix_ttc=25000.0,
                mention_neuf=True,
            ),
            cerfa=ExtractedCerfa(
                vin="VF1RFD00068123456",
                nom_titulaire="DUPONT",
                adresse="12 rue de la Paix",
                code_postal="75002",
                ville="Paris",
                puissance_fiscale_cv=7,
                signe=True,
            ),
            assurance=ExtractedAssurance(
                vin="VF1RFD00068123456",
                nom_assure="DUPONT",
                prenom_assure="Jean",
                date_effet=date(2026, 1, 1),
                date_echeance=date(2027, 1, 1),
                rc_incluse=True,
            ),
            attestation_identite_pro=True,
        )

    def test_complete_vn_dossier_vert_or_orange(self):
        docs = self._make_docs_vn()
        result = Phase1Pipeline().run(docs, reference_date=date(2026, 3, 26))
        # Dossier complet — VERT ou ORANGE (warnings VIN check digit possibles)
        assert result.diagnostic in (Diagnostic.VERT, Diagnostic.ORANGE)
        assert len(result.blocages) == 0

    def test_missing_cni_gives_rouge(self):
        docs = self._make_docs_vn()
        docs.identite = None
        result = Phase1Pipeline().run(docs, reference_date=date(2026, 3, 26))
        assert result.diagnostic == Diagnostic.ROUGE
        assert any(e["code"] == "V-01" for e in result.blocages)

    def test_missing_assurance_gives_rouge(self):
        docs = self._make_docs_vn()
        docs.assurance = None
        result = Phase1Pipeline().run(docs, reference_date=date(2026, 3, 26))
        assert result.diagnostic == Diagnostic.ROUGE
        assert any(e["code"] == "V-09" for e in result.blocages)

    def test_tax_estimate_present(self):
        docs = self._make_docs_vn()
        result = Phase1Pipeline().run(docs, reference_date=date(2026, 3, 26))
        assert result.tax_estimate is not None
        assert "total" in result.tax_estimate
        assert result.tax_estimate["total"] > 0
