"""Tests unitaires — AttestationFormationExtractor (formation moto 7h)."""
import pytest
from engine.extractors.attestation_formation import AttestationFormationExtractor

EXT = AttestationFormationExtractor()


# ── Cas nominal 125cc ─────────────────────────────────────────────────────────

ATTEST_125 = """
ATTESTATION DE FORMATION MOTO

Stagiaire : DUPONT Marine
Née le 05/06/1990

Formation dispensée le 12/04/2026
Durée : 7 heures
Type : 125 cm³ (A1/A2)
N° Attestation : ATT-2026-04567

Organisme de formation : AUTO-ÉCOLE DU CENTRE
Cachet et signature : [signature]
"""


def test_attest_125_success():
    r = EXT.extract_from_ocr_text(ATTEST_125)
    assert r.success is True
    assert r.data["nom_stagiaire"] == "DUPONT"
    assert r.data.get("prenom_stagiaire") is not None


def test_attest_125_date_formation():
    r = EXT.extract_from_ocr_text(ATTEST_125)
    assert r.data["date_formation"] == "2026-04-12"


def test_attest_125_duree():
    r = EXT.extract_from_ocr_text(ATTEST_125)
    assert r.data["duree_heures"] == 7


def test_attest_125_type():
    r = EXT.extract_from_ocr_text(ATTEST_125)
    assert r.data["type_formation"] == "125cc"


def test_attest_125_organisme():
    r = EXT.extract_from_ocr_text(ATTEST_125)
    assert r.data.get("organisme_formation") is not None


def test_attest_125_numero():
    r = EXT.extract_from_ocr_text(ATTEST_125)
    assert r.data["numero_attestation"] == "ATT-2026-04567"


def test_attest_125_signature():
    r = EXT.extract_from_ocr_text(ATTEST_125)
    assert r.data["signature_organisme"] is True


def test_attest_125_confidence():
    r = EXT.extract_from_ocr_text(ATTEST_125)
    assert r.confidence >= 0.85


# ── Cas L5e ───────────────────────────────────────────────────────────────────

ATTEST_L5E = """
Attestation de formation
Stagiaire : MARTIN Jean
Né le 10/12/1985

Formation réalisée le 05/03/2026
Durée : 7 heures
Catégorie L5e (triporteur)

Organisme : CENTRE DE CONDUITE EST
[SIGNÉE]
"""


def test_attest_l5e_success():
    r = EXT.extract_from_ocr_text(ATTEST_L5E)
    assert r.success is True
    assert r.data["type_formation"] == "L5e"


# ── Durée insuffisante → erreur ───────────────────────────────────────────────

ATTEST_5H = """
Attestation de Formation Moto
Stagiaire : BERNARD Sophie
Formation le 18/04/2026
Durée : 5 heures
"""


def test_attest_duree_insuffisante():
    r = EXT.extract_from_ocr_text(ATTEST_5H)
    # success peut être True (doc reconnu, nom trouvé) mais erreur signalée
    assert any("7h" in e or "insuffisan" in e.lower() or "minimum" in e.lower() for e in r.errors)


# ── Pas de signature (MISSING) ────────────────────────────────────────────────

ATTEST_NON_SIGNE = """
Attestation de Formation Moto
Stagiaire : LEROY Paul
Formation le 18/04/2026
Durée : 7 heures
[MISSING/BLANK]
"""


def test_attest_sans_signature():
    r = EXT.extract_from_ocr_text(ATTEST_NON_SIGNE)
    assert r.data["signature_organisme"] is False


# ── Document non reconnu ──────────────────────────────────────────────────────

def test_attest_inconnu():
    r = EXT.extract_from_ocr_text("Facture téléphonique — Orange — Mars 2026")
    assert r.success is False
    assert r.confidence <= 0.25


# ── Date naissance ────────────────────────────────────────────────────────────

def test_attest_date_naissance():
    r = EXT.extract_from_ocr_text(ATTEST_125)
    assert r.data["date_naissance"] == "1990-06-05"


# ── Permis B + 7h ────────────────────────────────────────────────────────────

ATTEST_B7H = """
Formation Permis B + 7
Stagiaire : PETIT Claire
Née le 25/08/2000
Formation moto réalisée le 01/04/2026
Durée : 7 heures
[signature]
"""


def test_attest_B7h_detecte():
    r = EXT.extract_from_ocr_text(ATTEST_B7H)
    assert r.success is True
