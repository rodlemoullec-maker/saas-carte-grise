"""Tests unitaires — AttestationHebergementExtractor."""
import pytest
from engine.extractors.attestation_hebergement import AttestationHebergementExtractor

EXT = AttestationHebergementExtractor()


# ── Cas nominal ───────────────────────────────────────────────────────────────

ATTEST_NOMINAL = """
ATTESTATION D'HÉBERGEMENT

Je soussigné MARTIN Jean-Pierre, certifie héberger à mon domicile :

Hébergé : DUPONT Marie
Adresse : 15 Rue des Lilas
75011 PARIS

Fait le 15/04/2026
[signature]
"""


def test_attest_success():
    r = EXT.extract_from_ocr_text(ATTEST_NOMINAL)
    assert r.success is True
    assert r.data["hebergeant_nom"] == "MARTIN"
    assert r.data.get("hebergeant_prenom") is not None


def test_attest_heberge():
    r = EXT.extract_from_ocr_text(ATTEST_NOMINAL)
    assert r.data["heberge_nom"] == "DUPONT"


def test_attest_code_postal():
    r = EXT.extract_from_ocr_text(ATTEST_NOMINAL)
    assert r.data["code_postal"] == "75011"
    assert r.data["ville"] == "PARIS"


def test_attest_date():
    r = EXT.extract_from_ocr_text(ATTEST_NOMINAL)
    assert r.data["date_attestation"] == "2026-04-15"


def test_attest_signature():
    r = EXT.extract_from_ocr_text(ATTEST_NOMINAL)
    assert r.data["signature_hebergeant"] is True


def test_attest_confidence():
    r = EXT.extract_from_ocr_text(ATTEST_NOMINAL)
    assert r.confidence >= 0.80


# ── Variante "certifie héberger" ──────────────────────────────────────────────

ATTEST_V2 = """
Je certifie héberger à titre gratuit à mon domicile
BERNARD Sophie née le 10/05/1998

Mon nom : LEROY François
Adresse : 8 Avenue de la Gare, 69001 LYON
Date : 18/04/2026
[SIGNÉE]
"""


def test_attest_variante_certifie():
    r = EXT.extract_from_ocr_text(ATTEST_V2)
    assert r.success is True


# ── Domicilié chez ────────────────────────────────────────────────────────────

ATTEST_DOMICILIE = """
Attestation hébergement
Hébergeant : PETIT André
Domicilié chez : 22 Rue du Moulin, 33000 BORDEAUX
Hébergé : PETIT Lucas
Fait le 01/03/2026
"""


def test_attest_domicilie():
    r = EXT.extract_from_ocr_text(ATTEST_DOMICILIE)
    assert r.success is True
    assert r.data["code_postal"] == "33000"


# ── Pas de signature ──────────────────────────────────────────────────────────

ATTEST_NON_SIGNE = """
Attestation d'hébergement
Je soussigné DUPONT Paul certifie héberger MARTIN Claire
Adresse : 5 Rue Nationale, 59000 LILLE
[MISSING/BLANK]
"""


def test_attest_sans_signature():
    r = EXT.extract_from_ocr_text(ATTEST_NON_SIGNE)
    assert r.data["signature_hebergeant"] is False


# ── Document non reconnu ──────────────────────────────────────────────────────

def test_attest_inconnu():
    r = EXT.extract_from_ocr_text("Relevé de compte BNP — Février 2026")
    assert r.success is False
    assert r.confidence <= 0.25


# ── Hébergeant seul (pas d'adresse) → confiance réduite ──────────────────────

ATTEST_SANS_ADRESSE = """
Attestation d'hébergement
Je soussigné MOREAU Christophe certifie héberger MOREAU Thomas.
Fait le 10/04/2026
[signature]
"""


def test_attest_sans_adresse_confidence():
    r = EXT.extract_from_ocr_text(ATTEST_SANS_ADRESSE)
    # Reconnu, hébergeant trouvé, mais pas d'adresse → confiance intermédiaire
    assert r.success is True
    assert 0.55 <= r.confidence <= 0.70
