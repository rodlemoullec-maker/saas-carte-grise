"""Tests unitaires — Cross-checks (C-rules)."""
from __future__ import annotations

from datetime import date

import pytest

from engine.cross_checks.siv_status import (
    DoublonVINCheck,
    GageCheck,
    OTCICheck,
    VECVEICheck,
    VolSignaleCheck,
)
from engine.cross_checks.vo_checks import (
    ChaineProprieteCheck,
    DatesCGBarreeCheck,
    SignaturesCotitulaireCheck,
)
from engine.cross_checks.coc_cerfa_checks import (
    CNITUTACCheck,
    CO2WLTPCheck,
    PuissanceFiscaleCheck,
)
from engine.cross_checks.address_checks import AddressCerfaDomicileCheck
from engine.models.decision import CrossCheckStatus
from engine.models.documents import (
    ExtractedCerfa,
    ExtractedCGBarree,
    ExtractedCession,
    ExtractedCOC,
    ExtractedDA,
    ExtractedDomicile,
    ExtractedHistoVec,
    ExtractedRecepisseDA,
)


# ─── SIV Status (C-17 → C-21) ────────────────────────────────────────────────

class TestGageCheck:

    def test_no_gage(self):
        h = ExtractedHistoVec(immatriculation="AA-123-BB", gage_actif=False, otci_active=False, vol_signale=False, vec=False, vei=False)
        results = GageCheck().run(h)
        assert all(r.status == CrossCheckStatus.PASS for r in results)

    def test_gage_actif(self):
        h = ExtractedHistoVec(immatriculation="AA-123-BB", gage_actif=True, otci_active=False, vol_signale=False, vec=False, vei=False)
        results = GageCheck().run(h)
        assert any(r.status == CrossCheckStatus.FAIL for r in results)


class TestVolSignaleCheck:

    def test_no_vol(self):
        h = ExtractedHistoVec(immatriculation="AA-123-BB", gage_actif=False, otci_active=False, vol_signale=False, vec=False, vei=False)
        results = VolSignaleCheck().run(h)
        assert all(r.status == CrossCheckStatus.PASS for r in results)

    def test_vol_signale(self):
        h = ExtractedHistoVec(immatriculation="AA-123-BB", gage_actif=False, otci_active=False, vol_signale=True, vec=False, vei=False)
        results = VolSignaleCheck().run(h)
        assert any(r.status == CrossCheckStatus.FAIL and "vol" in (r.detail or "").lower() for r in results)


class TestVECVEICheck:

    def test_clean(self):
        h = ExtractedHistoVec(immatriculation="AA-123-BB", gage_actif=False, otci_active=False, vol_signale=False, vec=False, vei=False)
        results = VECVEICheck().run(h)
        assert all(r.status == CrossCheckStatus.PASS for r in results)

    def test_vec(self):
        h = ExtractedHistoVec(immatriculation="AA-123-BB", gage_actif=False, otci_active=False, vol_signale=False, vec=True, vei=False)
        results = VECVEICheck().run(h)
        assert any(r.status == CrossCheckStatus.FAIL and r.rule_name == "vec_status" for r in results)

    def test_vei(self):
        h = ExtractedHistoVec(immatriculation="AA-123-BB", gage_actif=False, otci_active=False, vol_signale=False, vec=False, vei=True)
        results = VECVEICheck().run(h)
        assert any(r.status == CrossCheckStatus.FAIL and r.rule_name == "vei_status" for r in results)


class TestDoublonVINCheck:

    def test_no_doublon(self):
        results = DoublonVINCheck().run("VF1RFD00068123456", [], "dossier-1")
        assert all(r.status == CrossCheckStatus.PASS for r in results)

    def test_doublon_detected(self):
        results = DoublonVINCheck().run("VF1RFD00068123456", ["dossier-2"], "dossier-1")
        assert any(r.status == CrossCheckStatus.FAIL for r in results)

    def test_same_dossier_excluded(self):
        results = DoublonVINCheck().run("VF1RFD00068123456", ["dossier-1"], "dossier-1")
        assert all(r.status == CrossCheckStatus.PASS for r in results)


# ─── VO Checks (C-11 → C-14) ─────────────────────────────────────────────────

class TestChaineProprieteCheck:

    def test_matching_names(self):
        cg = ExtractedCGBarree(
            vin="VF1RFD00068123456", titulaire_nom="DUPONT Jean",
            signatures_count=1, co_titulaires_count=1,
        )
        da = ExtractedDA(vin="VF1RFD00068123456", vendeur_nom="DUPONT Jean")
        results = ChaineProprieteCheck().run(cg, da)
        assert any(r.rule_name == "vendeur_da_vs_titulaire_cg" and r.status == CrossCheckStatus.PASS for r in results)

    def test_mismatched_names(self):
        cg = ExtractedCGBarree(
            vin="VF1RFD00068123456", titulaire_nom="DUPONT Jean",
            signatures_count=1, co_titulaires_count=1,
        )
        da = ExtractedDA(vin="VF1RFD00068123456", vendeur_nom="MARTIN Pierre")
        results = ChaineProprieteCheck().run(cg, da)
        assert any(r.rule_name == "vendeur_da_vs_titulaire_cg" and r.status == CrossCheckStatus.FAIL for r in results)

    def test_vin_mismatch(self):
        cg = ExtractedCGBarree(
            vin="VF1RFD00068123456", titulaire_nom="DUPONT",
            signatures_count=1, co_titulaires_count=1,
        )
        da = ExtractedDA(vin="WBA3A5C50CF123456", vendeur_nom="DUPONT")
        results = ChaineProprieteCheck().run(cg, da)
        assert any(r.rule_name == "vin_cg_vs_da" and r.status == CrossCheckStatus.FAIL for r in results)


class TestDatesCGBarreeCheck:

    def test_dates_chronological(self):
        cg = ExtractedCGBarree(
            vin="X", date_vente=date(2026, 3, 1),
            signatures_count=1, co_titulaires_count=1,
        )
        da = ExtractedDA(vin="X", date_achat=date(2026, 3, 1))
        cession = ExtractedCession(vin="X", date_cession=date(2026, 3, 15))
        results = DatesCGBarreeCheck().run(cg, da, cession)
        assert all(r.status == CrossCheckStatus.PASS for r in results)

    def test_cg_after_da(self):
        cg = ExtractedCGBarree(
            vin="X", date_vente=date(2026, 3, 20),
            signatures_count=1, co_titulaires_count=1,
        )
        da = ExtractedDA(vin="X", date_achat=date(2026, 3, 10))
        results = DatesCGBarreeCheck().run(cg, da)
        assert any(r.rule_name == "cg_date_vs_da_date" and r.status == CrossCheckStatus.FAIL for r in results)

    def test_recepisse_too_late(self):
        cg = ExtractedCGBarree(vin="X", signatures_count=1, co_titulaires_count=1)
        da = ExtractedDA(vin="X", date_achat=date(2026, 3, 1))
        recepisse = ExtractedRecepisseDA(vin="X", date_enregistrement=date(2026, 3, 25))
        results = DatesCGBarreeCheck().run(cg, da, recepisse=recepisse)
        assert any(r.rule_name == "recepisse_da_delay" and r.status == CrossCheckStatus.FAIL for r in results)


class TestSignaturesCotitulaireCheck:

    def test_enough_signatures(self):
        cg = ExtractedCGBarree(vin="X", signatures_count=2, co_titulaires_count=2)
        results = SignaturesCotitulaireCheck().run(cg)
        assert any(r.status == CrossCheckStatus.PASS for r in results)

    def test_not_enough_signatures(self):
        cg = ExtractedCGBarree(vin="X", signatures_count=1, co_titulaires_count=3)
        results = SignaturesCotitulaireCheck().run(cg)
        assert any(r.status == CrossCheckStatus.FAIL for r in results)


# ─── COC / Cerfa (C-08 → C-10) ──────────────────────────────────────────────

class TestCNITUTACCheck:

    def test_cnit_valid_format(self):
        coc = ExtractedCOC(vin="VF1RFD00068123456", marque="RENAULT", energie="Essence", cnit="AB12345C")
        results = CNITUTACCheck().run(coc)
        assert any(r.status == CrossCheckStatus.PASS for r in results)

    def test_cnit_missing(self):
        coc = ExtractedCOC(vin="VF1RFD00068123456", marque="RENAULT", energie="Essence", cnit=None)
        results = CNITUTACCheck().run(coc)
        assert any(r.status == CrossCheckStatus.WARNING for r in results)


class TestPuissanceFiscaleCheck:

    def test_matching(self):
        coc = ExtractedCOC(vin="X", marque="X", energie="X", puissance_fiscale_cv=7)
        cerfa = ExtractedCerfa(puissance_fiscale_cv=7)
        results = PuissanceFiscaleCheck().run(coc, cerfa)
        assert all(r.status == CrossCheckStatus.PASS for r in results)

    def test_delta_1cv_warning(self):
        coc = ExtractedCOC(vin="X", marque="X", energie="X", puissance_fiscale_cv=7)
        cerfa = ExtractedCerfa(puissance_fiscale_cv=6)
        results = PuissanceFiscaleCheck().run(coc, cerfa)
        assert any(r.status == CrossCheckStatus.WARNING for r in results)

    def test_delta_3cv_blocking(self):
        coc = ExtractedCOC(vin="X", marque="X", energie="X", puissance_fiscale_cv=10)
        cerfa = ExtractedCerfa(puissance_fiscale_cv=6)
        results = PuissanceFiscaleCheck().run(coc, cerfa)
        assert any(r.status == CrossCheckStatus.FAIL for r in results)


class TestCO2WLTPCheck:

    def test_wltp_only(self):
        coc = ExtractedCOC(vin="X", marque="X", energie="Essence", co2_wltp=130.0)
        results = CO2WLTPCheck().run(coc)
        assert any(r.status == CrossCheckStatus.PASS for r in results)

    def test_electric_no_co2(self):
        coc = ExtractedCOC(vin="X", marque="X", energie="Electrique")
        results = CO2WLTPCheck().run(coc)
        assert any(r.status == CrossCheckStatus.PASS for r in results)

    def test_nedc_only_post2021(self):
        coc = ExtractedCOC(
            vin="X", marque="X", energie="Essence",
            co2_nedc=120.0, date_premiere_immat_ue=date(2022, 1, 1),
        )
        results = CO2WLTPCheck().run(coc)
        assert any(r.status == CrossCheckStatus.FAIL for r in results)


# ─── Adresse (C-04) ─────────────────────────────────────────────────────────

class TestAddressCerfaDomicileCheck:

    def test_matching_address(self):
        cerfa = ExtractedCerfa(adresse="12 rue de la Paix", code_postal="75002", ville="Paris")
        domicile = ExtractedDomicile(
            nom_titulaire="DUPONT", adresse_ligne1="12 rue de la Paix", code_postal="75002",
            ville="Paris", date_document=date(2026, 1, 1),
        )
        results = AddressCerfaDomicileCheck().run(cerfa, domicile)
        assert any(r.status == CrossCheckStatus.PASS for r in results)

    def test_different_cp(self):
        cerfa = ExtractedCerfa(code_postal="75002", ville="Paris")
        domicile = ExtractedDomicile(
            nom_titulaire="DUPONT", adresse_ligne1="X", code_postal="69001",
            ville="Lyon", date_document=date(2026, 1, 1),
        )
        results = AddressCerfaDomicileCheck().run(cerfa, domicile)
        assert any(r.status == CrossCheckStatus.FAIL for r in results)
