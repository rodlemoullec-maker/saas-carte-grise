"""Tests unitaires — Validators de dates (V-11→V-19)."""
from __future__ import annotations

from datetime import date, timedelta

import pytest

from engine.validators.dates import (
    AgeValidator,
    CodeCessionValidator,
    DocumentDateValidator,
    KbisValidator,
    TitreSejourValidator,
)


class TestDocumentDateValidator:

    def setup_method(self):
        self.v = DocumentDateValidator()
        self.ref = date(2026, 3, 26)

    # V-11 : CNI
    def test_cni_valid(self):
        result = self.v.validate("identite", date(2030, 1, 1), self.ref)
        assert result.valid is True

    def test_cni_expired_less_than_5y(self):
        result = self.v.validate("identite", date(2023, 1, 1), self.ref)
        assert result.valid is True  # WARNING, not blocking
        assert len(result.warnings) > 0
        assert any("EXPIRED_WITHIN_5Y" in w.code for w in result.warnings)

    def test_cni_expired_more_than_5y(self):
        result = self.v.validate("identite", date(2018, 1, 1), self.ref)
        assert result.valid is False
        assert any(e.code == "IDENTITY_DOC_EXPIRED" for e in result.errors)

    # V-12 : Permis
    def test_permis_valid(self):
        result = self.v.validate("permis", date(2030, 1, 1), self.ref)
        assert result.valid is True

    def test_permis_expired(self):
        result = self.v.validate("permis", date(2025, 12, 1), self.ref)
        assert result.valid is False
        assert any(e.code == "DRIVING_LICENSE_EXPIRED" for e in result.errors)

    # V-14 : Justificatif domicile
    def test_domicile_recent(self):
        result = self.v.validate("facture_electricite", date(2026, 2, 1), self.ref)
        assert result.valid is True

    def test_domicile_too_old(self):
        result = self.v.validate("facture_electricite", date(2025, 6, 1), self.ref)
        assert result.valid is False
        assert any(e.code == "DOMICILE_TOO_OLD" for e in result.errors)

    def test_attestation_hebergement_no_expiry(self):
        result = self.v.validate("attestation_hebergement", date(2020, 1, 1), self.ref)
        assert result.valid is True  # Pas de délai

    # V-19 : Assurance
    def test_assurance_expired(self):
        result = self.v.validate("assurance_echeance", date(2026, 3, 1), self.ref)
        assert result.valid is False

    def test_assurance_not_yet_active(self):
        result = self.v.validate("assurance_effet", date(2026, 4, 1), self.ref)
        assert result.valid is False


class TestAgeValidator:
    """Tests C-16 : âge ↔ catégorie permis."""

    def setup_method(self):
        self.v = AgeValidator()
        self.ref = date(2026, 3, 26)

    def test_adult_no_issues(self):
        ddn = date(2000, 1, 1)  # 26 ans
        result = self.v.validate(ddn, reference_date=self.ref)
        assert result.valid is True

    def test_child_under_14_blocked(self):
        ddn = date(2013, 6, 1)  # 12 ans
        result = self.v.validate(ddn, reference_date=self.ref)
        assert result.valid is False
        assert any(e.code == "BUYER_TOO_YOUNG" for e in result.errors)

    def test_minor_14_AM_only(self):
        ddn = date(2012, 1, 1)  # 14 ans
        result = self.v.validate(ddn, permis_categories=["B"], reference_date=self.ref)
        assert result.valid is False
        assert any(e.code == "AGE_CATEGORY_MISMATCH" for e in result.errors)

    def test_minor_14_AM_ok(self):
        ddn = date(2012, 1, 1)  # 14 ans
        result = self.v.validate(ddn, permis_categories=["AM"], reference_date=self.ref)
        # Valid car AM autorisé, mais WARNING mineur
        assert any(w.code == "BUYER_UNDERAGE_ESCALADE" for w in result.warnings)

    def test_minor_16_A1_ok(self):
        ddn = date(2010, 1, 1)  # 16 ans
        result = self.v.validate(ddn, permis_categories=["A1"], reference_date=self.ref)
        assert not any(e.code == "AGE_CATEGORY_MISMATCH" for e in result.errors)

    def test_minor_16_B_blocked(self):
        ddn = date(2010, 1, 1)  # 16 ans
        result = self.v.validate(ddn, permis_categories=["B"], reference_date=self.ref)
        assert any(e.code == "AGE_CATEGORY_MISMATCH" for e in result.errors)


class TestCodeCessionValidator:
    """Tests V-18."""

    def setup_method(self):
        self.v = CodeCessionValidator()

    def test_code_valid(self):
        result = self.v.validate(date(2026, 3, 20), reference_date=date(2026, 3, 26))
        assert result.valid is True

    def test_code_expired(self):
        result = self.v.validate(date(2026, 3, 1), reference_date=date(2026, 3, 26))
        assert result.valid is False

    def test_code_skipped_for_pro_siv(self):
        result = self.v.validate(date(2026, 1, 1), pro_habilite_siv=True, reference_date=date(2026, 3, 26))
        assert result.valid is True


class TestTitreSejourValidator:
    """Tests V-13."""

    def setup_method(self):
        self.v = TitreSejourValidator()

    def test_valid(self):
        result = self.v.validate(date(2027, 1, 1), reference_date=date(2026, 3, 26))
        assert result.valid is True

    def test_expired(self):
        result = self.v.validate(date(2026, 2, 1), reference_date=date(2026, 3, 26))
        assert result.valid is False
        assert any(e.code == "TITRE_SEJOUR_EXPIRED" for e in result.errors)

    def test_expiring_soon(self):
        result = self.v.validate(date(2026, 4, 10), reference_date=date(2026, 3, 26))
        assert result.valid is True
        assert any(e.code == "TITRE_SEJOUR_EXPIRING" for e in result.warnings)

    def test_recepisse_warning(self):
        result = self.v.validate(date(2026, 6, 1), is_recepisse=True, reference_date=date(2026, 3, 26))
        assert result.valid is True
        assert any(e.code == "TITRE_SEJOUR_RECEPISSE" for e in result.warnings)


class TestKbisValidator:
    """Tests V-15."""

    def setup_method(self):
        self.v = KbisValidator()

    def test_fresh_kbis(self):
        result = self.v.validate(date(2026, 2, 1), reference_date=date(2026, 3, 26))
        assert result.valid is True

    def test_kbis_too_old(self):
        result = self.v.validate(date(2025, 11, 1), reference_date=date(2026, 3, 26))
        assert result.valid is False
        assert any(e.code == "KBIS_TOO_OLD" for e in result.errors)

    def test_kbis_expiring_soon(self):
        result = self.v.validate(date(2026, 1, 5), reference_date=date(2026, 3, 26))
        assert result.valid is True
        assert any(e.code == "KBIS_EXPIRING_SOON" for e in result.warnings)
