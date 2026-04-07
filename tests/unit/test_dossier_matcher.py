"""
Tests unitaires pour engine.dossier_matcher

Couvre les fonctions pures (sans accès BDD) :
- _normalize, _normalize_phone, _fuzzy_score, _normalize_immat
- _score_dossier (toutes les stratégies de match)
- merge_hints
- DossierMatch dataclass
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from engine.dossier_matcher import (
    DossierMatch,
    _fuzzy_score,
    _normalize,
    _normalize_immat,
    _normalize_phone,
    _score_dossier,
    merge_hints,
)


# ─── Mock DossierDB ─────────────────────────────────────────────────────────


@dataclass
class FakeDossier:
    """Mock minimal de DossierDB pour les tests de matching."""
    id: str = "fake-id-1"
    reference: str = "CG-2026-12345"
    client_nom: str | None = None
    client_prenom: str | None = None
    client_email: str | None = None
    client_telephone: str | None = None
    vin: str | None = None
    immatriculation: str | None = None
    type: str | None = None
    status: str = "PENDING"
    created_at: datetime | None = None


# ─── Normalisation ─────────────────────────────────────────────────────────


class TestNormalize:
    def test_lowercase(self) -> None:
        assert _normalize("DUPONT") == "dupont"

    def test_strip_accents(self) -> None:
        assert _normalize("Étienne") == "etienne"
        assert _normalize("Hélène") == "helene"
        assert _normalize("François") == "francois"

    def test_strip_whitespace(self) -> None:
        assert _normalize("  Marie  ") == "marie"

    def test_empty_returns_empty(self) -> None:
        assert _normalize(None) == ""
        assert _normalize("") == ""


class TestNormalizePhone:
    def test_keeps_only_digits(self) -> None:
        assert _normalize_phone("06 12 34 56 78") == "0612345678"

    def test_handles_dots(self) -> None:
        assert _normalize_phone("06.12.34.56.78") == "0612345678"

    def test_converts_plus33(self) -> None:
        assert _normalize_phone("+33612345678") == "0612345678"
        assert _normalize_phone("+33 6 12 34 56 78") == "0612345678"

    def test_empty(self) -> None:
        assert _normalize_phone(None) == ""
        assert _normalize_phone("") == ""


class TestNormalizeImmat:
    def test_strip_dashes(self) -> None:
        assert _normalize_immat("AB-123-CD") == "AB123CD"

    def test_uppercase(self) -> None:
        assert _normalize_immat("ab-123-cd") == "AB123CD"

    def test_strip_spaces(self) -> None:
        assert _normalize_immat("AB 123 CD") == "AB123CD"

    def test_empty(self) -> None:
        assert _normalize_immat(None) == ""
        assert _normalize_immat("") == ""


class TestFuzzyScore:
    def test_exact_match_returns_one(self) -> None:
        assert _fuzzy_score("DUPONT", "DUPONT") == 1.0

    def test_case_insensitive(self) -> None:
        assert _fuzzy_score("DUPONT", "dupont") == 1.0

    def test_accent_insensitive(self) -> None:
        assert _fuzzy_score("Étienne", "etienne") == 1.0

    def test_typo_high_score(self) -> None:
        # Une faute de frappe → score élevé mais < 1.0
        score = _fuzzy_score("DUPONT", "DUPOMT")
        assert 0.8 < score < 1.0

    def test_completely_different_low_score(self) -> None:
        score = _fuzzy_score("DUPONT", "MARTIN")
        assert score < 0.6

    def test_empty_returns_zero(self) -> None:
        assert _fuzzy_score("", "DUPONT") == 0.0
        assert _fuzzy_score("DUPONT", "") == 0.0


# ─── Stratégies de scoring ─────────────────────────────────────────────────


class TestScoreDossier:
    def test_vin_exact_match_top_score(self) -> None:
        d = FakeDossier(vin="JMZKECW105SJ08739")
        score, reason = _score_dossier(d, {"vin": "JMZKECW105SJ08739"})
        assert score == 1.0
        assert reason == "vin"

    def test_vin_case_insensitive(self) -> None:
        d = FakeDossier(vin="jmzkecw105sj08739")
        score, reason = _score_dossier(d, {"vin": "JMZKECW105SJ08739"})
        assert score == 1.0
        assert reason == "vin"

    def test_immatriculation_exact_match(self) -> None:
        d = FakeDossier(immatriculation="AB-123-CD")
        score, reason = _score_dossier(d, {"immatriculation": "AB123CD"})
        assert score == 0.95
        assert reason == "immatriculation"

    def test_nom_prenom_exacts(self) -> None:
        d = FakeDossier(client_nom="DUPONT", client_prenom="Marie")
        score, reason = _score_dossier(d, {"client_nom": "DUPONT", "client_prenom": "Marie"})
        assert score == 0.85
        assert reason == "nom_exact"

    def test_nom_seul_exact(self) -> None:
        d = FakeDossier(client_nom="DUPONT")
        score, reason = _score_dossier(d, {"client_nom": "DUPONT"})
        assert score == 0.80
        assert reason == "nom_exact"

    def test_email_exact(self) -> None:
        d = FakeDossier(client_email="marie@example.fr")
        score, reason = _score_dossier(d, {"sender_email": "marie@example.fr"})
        assert score == 0.80
        assert reason == "email"

    def test_telephone_exact(self) -> None:
        d = FakeDossier(client_telephone="0612345678")
        score, reason = _score_dossier(d, {"phone": "+33612345678"})
        assert score == 0.80
        assert reason == "telephone"

    def test_nom_fuzzy_high(self) -> None:
        """Faute de frappe (lettre dupliquée) — match fuzzy ≥ 0.90."""
        # DUPONTT vs DUPONT → ratio difflib 0.92, dépasse le seuil 0.90
        d = FakeDossier(client_nom="DUPONT", client_prenom="Marie")
        score, reason = _score_dossier(d, {"client_nom": "DUPONTT", "client_prenom": "Marie"})
        assert score >= 0.75
        assert reason == "nom_fuzzy"

    def test_no_match_returns_zero(self) -> None:
        d = FakeDossier(
            client_nom="DUPONT",
            vin="JMZKECW105SJ08739",
            client_email="marie@gmail.com",
        )
        score, reason = _score_dossier(d, {
            "client_nom": "MARTIN",
            "vin": "WBA1234567890ABCD",
            "sender_email": "paul@yahoo.fr",
        })
        assert score == 0.0
        assert reason == "none"

    def test_vin_priority_over_nom(self) -> None:
        """VIN match doit l'emporter sur un nom différent."""
        d = FakeDossier(vin="JMZKECW105SJ08739", client_nom="DUPONT")
        score, reason = _score_dossier(d, {
            "vin": "JMZKECW105SJ08739",
            "client_nom": "MARTIN",  # nom différent
        })
        assert score == 1.0
        assert reason == "vin"


# ─── merge_hints ────────────────────────────────────────────────────────────


class TestMergeHints:
    def test_merge_two_dicts(self) -> None:
        merged = merge_hints(
            {"vin": "ABC123"},
            {"client_nom": "DUPONT"},
        )
        assert merged == {"vin": "ABC123", "client_nom": "DUPONT"}

    def test_later_wins(self) -> None:
        merged = merge_hints(
            {"vin": "OLD"},
            {"vin": "NEW"},
        )
        assert merged["vin"] == "NEW"

    def test_empty_values_ignored(self) -> None:
        merged = merge_hints(
            {"vin": "ABC"},
            {"vin": "", "client_nom": None, "ok": "yes"},
        )
        assert merged == {"vin": "ABC", "ok": "yes"}

    def test_handles_none_dict(self) -> None:
        merged = merge_hints(None, {"a": "b"}, None, {"c": "d"})  # type: ignore
        assert merged == {"a": "b", "c": "d"}


# ─── DossierMatch ───────────────────────────────────────────────────────────


class TestDossierMatch:
    def test_create_match(self) -> None:
        m = DossierMatch(
            dossier_id="abc",
            reference="CG-2026-12345",
            client_nom="DUPONT",
            client_prenom="Marie",
            vin="ABC123",
            immatriculation="AB123CD",
            type="VN",
            status="PENDING",
            confidence=0.95,
            match_reason="immatriculation",
            created_at=None,
        )
        assert m.confidence == 0.95
        assert m.match_reason == "immatriculation"
