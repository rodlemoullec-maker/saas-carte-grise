"""Tests unitaires — SIRETValidator."""
from __future__ import annotations
from engine.validators.siret import SIRETValidator


class TestSIRETValidator:

    def setup_method(self):
        self.validator = SIRETValidator()

    def test_valid_siret(self):
        # SIRET INSEE valide (clé Luhn correcte)
        result = self.validator.validate("73282932000074")
        assert result.valid is True

    def test_too_short(self):
        result = self.validator.validate("1234567890123")  # 13 chars
        assert result.valid is False
        assert any(e.code == "SIRET_LENGTH_INVALID" for e in result.errors)

    def test_non_numeric(self):
        result = self.validator.validate("7328293200007A")
        assert result.valid is False

    def test_spaces_normalized(self):
        result = self.validator.validate("732 829 320 00074")
        assert result.valid is True

    def test_invalid_luhn(self):
        result = self.validator.validate("73282932000075")  # Clé Luhn fausse
        assert result.valid is False
