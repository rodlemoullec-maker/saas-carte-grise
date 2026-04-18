"""Tests unitaires — KbisExtractor."""
import pytest
from engine.extractors.kbis import KbisExtractor

EXT = KbisExtractor()


# ── Cas nominal Kbis ──────────────────────────────────────────────────────────

KBIS_NOMINAL = """
EXTRAIT REGISTRE DU COMMERCE ET DES SOCIÉTÉS
Kbis — Tribunal de Commerce de Paris

Dénomination : AUTO PREMIUM SAS
SIREN : 123 456 789
SIRET : 123 456 789 00014
Gérant : MARTIN François
Siège social : 12 Rue de la Paix, 75001 Paris

Délivré le 18/04/2026
"""


def test_kbis_success():
    r = EXT.extract_from_ocr_text(KBIS_NOMINAL)
    assert r.success is True
    assert r.data["siren"] == "123456789"
    assert r.data["siret_siege"] == "12345678900014"
    assert r.data["raison_sociale"] == "AUTO PREMIUM SAS"


def test_kbis_representant():
    r = EXT.extract_from_ocr_text(KBIS_NOMINAL)
    assert r.data["representant_nom"] == "MARTIN"
    assert r.data["representant_prenom"] == "François"


def test_kbis_date():
    r = EXT.extract_from_ocr_text(KBIS_NOMINAL)
    assert r.data["date_kbis"] == "2026-04-18"


def test_kbis_confidence_haute():
    r = EXT.extract_from_ocr_text(KBIS_NOMINAL)
    assert r.confidence >= 0.85


# ── Avis SIRENE ───────────────────────────────────────────────────────────────

AVIS_SIRENE = """
AVIS SIRENE
Entreprise immatriculée au SIRENE
Raison sociale : GARAGE DU SOLEIL SARL
SIREN 987654321
Dirigeant : DUPONT Jean
Adresse : 5 Avenue Foch, 69001 Lyon
"""


def test_sirene_success():
    r = EXT.extract_from_ocr_text(AVIS_SIRENE)
    assert r.success is True
    assert r.data["siren"] == "987654321"


def test_sirene_raison_sociale():
    r = EXT.extract_from_ocr_text(AVIS_SIRENE)
    assert "GARAGE DU SOLEIL" in r.data.get("raison_sociale", "")


# ── SIREN déduit du SIRET ─────────────────────────────────────────────────────

KBIS_SIRET_ONLY = """
Kbis extrait le 01/03/2026
Société : MOTO CENTER EURL
SIRET 321 654 987 00025
Gérant : BERNARD Sophie
"""


def test_siren_deduit_du_siret():
    r = EXT.extract_from_ocr_text(KBIS_SIRET_ONLY)
    assert r.data["siren"] == "321654987"
    assert r.data["siret_siege"] == "32165498700025"


# ── Échec sans SIREN ni mention Kbis ─────────────────────────────────────────

def test_kbis_inconnu():
    r = EXT.extract_from_ocr_text("Facture EDF n° 12345 — Montant 89,50 €")
    assert r.success is False
    assert r.confidence <= 0.25


# ── Confiance intermédiaire (Kbis reconnu mais SIREN manquant) ────────────────

KBIS_SANS_SIREN = """
Extrait Registre du Commerce
Dénomination : TEST SA
Gérant : TEST Jean
"""


def test_kbis_sans_siren_confidence():
    r = EXT.extract_from_ocr_text(KBIS_SANS_SIREN)
    assert r.success is False
    assert 0.40 <= r.confidence <= 0.60


# ── Adresse siège ─────────────────────────────────────────────────────────────

def test_kbis_adresse():
    r = EXT.extract_from_ocr_text(KBIS_NOMINAL)
    assert r.data.get("adresse_siege") is not None
    assert "Paris" in r.data["adresse_siege"]
