"""Tests unitaires — VINValidator."""
from __future__ import annotations
import pytest
from engine.validators.vin import VINValidator


class TestVINValidator:

    def setup_method(self):
        self.validator = VINValidator()

    def test_valid_vin(self, sample_vin_valid):
        result = self.validator.validate(sample_vin_valid)
        assert result.valid is True
        assert not result.is_blocking

    def test_invalid_length_short(self):
        result = self.validator.validate("VF1RFD0006812345")  # 16 chars
        assert result.valid is False
        assert any(e.code == "VIN_LENGTH_INVALID" for e in result.errors)

    def test_invalid_length_long(self):
        result = self.validator.validate("VF1RFD000681234567")  # 18 chars
        assert result.valid is False

    def test_forbidden_char_O(self):
        result = self.validator.validate("VF1RFD0006O123456")
        assert result.valid is False
        assert any(e.code == "VIN_FORBIDDEN_CHAR" for e in result.errors)

    def test_forbidden_char_I(self):
        result = self.validator.validate("VF1RFD0006I123456")
        assert result.valid is False

    def test_forbidden_char_Q(self):
        result = self.validator.validate("VF1RFD0006Q123456")
        assert result.valid is False

    def test_whitespace_normalized(self):
        result = self.validator.validate("VF1 RFD 000 68123 456")
        assert result.valid is True

    def test_dashes_normalized(self):
        result = self.validator.validate("VF1-RFD-000-68-123456")
        assert result.valid is True
