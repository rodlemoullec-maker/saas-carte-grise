"""Tests unitaires — DAExtractor (Déclaration d'Achat Cerfa 13751)."""
import pytest
from engine.extractors.da import DAExtractor

EXT = DAExtractor()


# ── Cas nominal ───────────────────────────────────────────────────────────────

DA_NOMINALE = """
DÉCLARATION D'ACHAT
Cerfa n° 13751*05

Acheteur professionnel :
Raison sociale : MOTO CITY SARL
SIRET : 456 789 123 00021
Date d'achat : 15/04/2026
Vendeur : MARTIN René

Véhicule :
Immatriculation : GH-789-IJ
VIN : WAUZZZ4B21N012345
"""


def test_da_success():
    r = EXT.extract_from_ocr_text(DA_NOMINALE)
    assert r.success is True
    assert r.data["vin"] == "WAUZZZ4B21N012345"
    assert r.data["immatriculation"] == "GH-789-IJ"
    assert r.data["siret_pro"] == "45678912300021"
    assert r.data["siren_pro"] == "456789123"


def test_da_date_achat():
    r = EXT.extract_from_ocr_text(DA_NOMINALE)
    assert r.data["date_achat"] == "2026-04-15"


def test_da_nom_pro():
    r = EXT.extract_from_ocr_text(DA_NOMINALE)
    assert r.data.get("nom_pro") is not None
    assert "MOTO CITY" in r.data["nom_pro"]


def test_da_vendeur():
    r = EXT.extract_from_ocr_text(DA_NOMINALE)
    assert r.data.get("vendeur_nom") is not None


def test_da_confidence_haute():
    r = EXT.extract_from_ocr_text(DA_NOMINALE)
    assert r.confidence >= 0.85


# ── Cerfa reconnu par numéro ──────────────────────────────────────────────────

DA_PAR_NUM = """
Cerfa 13751
SIRET 789012345 00033
Immatriculation : KL-456-MN
VIN : 1HGBH41JXMN109186
Date d'achat : 01/01/2025
"""


def test_da_reconnu_par_numero_cerfa():
    r = EXT.extract_from_ocr_text(DA_PAR_NUM)
    assert r.success is True


# ── Échec sans VIN ni immat ───────────────────────────────────────────────────

DA_SANS_VEHICULE = """
Déclaration d'Achat
SIRET : 111 222 333 00044
"""


def test_da_sans_vehicule_failure():
    r = EXT.extract_from_ocr_text(DA_SANS_VEHICULE)
    assert r.success is False
    assert any("VIN" in e or "immatriculat" in e.lower() for e in r.errors)


# ── Échec non reconnu ────────────────────────────────────────────────────────

def test_da_document_inconnu():
    r = EXT.extract_from_ocr_text("Quittance de loyer — Janvier 2026")
    assert r.success is False
    assert r.confidence <= 0.25


# ── SIREN seul (pas de SIRET) ─────────────────────────────────────────────────

DA_SIREN_SEUL = """
Déclaration d'Achat Cerfa 13751
SIREN 222 333 444
Immatriculation : OP-012-QR
VIN : JN1AZNX11Z0000001
"""


def test_da_siren_seul():
    r = EXT.extract_from_ocr_text(DA_SIREN_SEUL)
    assert r.data["siren_pro"] == "222333444"


# ── Confiance intermédiaire (DA sans SIREN) ───────────────────────────────────

DA_SANS_SIREN = """
Déclaration d'achat
Immatriculation : ST-345-UV
VIN : 1HGBH41JXMN109186
"""


def test_da_sans_siren_confidence():
    r = EXT.extract_from_ocr_text(DA_SANS_SIREN)
    assert r.success is False
    assert 0.40 <= r.confidence <= 0.70
