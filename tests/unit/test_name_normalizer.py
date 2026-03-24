"""Tests unitaires — Normalisation et matching des noms."""
from __future__ import annotations
from engine.normalizers.names import match_names, normalize_name


class TestNormalizeName:

    def test_basic(self):
        assert normalize_name("martin") == "MARTIN"

    def test_accents_removed(self):
        assert normalize_name("Léa") == "LEA"

    def test_hyphen_to_space(self):
        assert normalize_name("Jean-Pierre") == "JEAN PIERRE"

    def test_multiple_spaces(self):
        assert normalize_name("  Jean   Pierre  ") == "JEAN PIERRE"


class TestMatchNames:

    def test_exact_match(self):
        result = match_names("MARTIN", "MARTIN")
        assert result.matched is True
        assert result.confidence == 1.0

    def test_case_insensitive(self):
        result = match_names("martin", "MARTIN")
        assert result.matched is True

    def test_accent_insensitive(self):
        result = match_names("Léa Dupont", "LEA DUPONT")
        assert result.matched is True

    def test_different_order(self):
        result = match_names("JEAN PIERRE", "PIERRE JEAN")
        assert result.matched is True

    def test_clearly_different(self):
        result = match_names("MARTIN", "BERNARD")
        assert result.matched is False

    def test_fuzzy_match_typo(self):
        result = match_names("DUPONT", "DUPONTT")
        assert result.confidence >= 0.85
