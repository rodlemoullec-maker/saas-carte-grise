"""Tests unitaires — RecepissedaExtractor (Récépissé de DA)."""
import pytest
from engine.extractors.recepisseDA import RecepissedaExtractor

EXT = RecepissedaExtractor()


# ── Cas nominal ───────────────────────────────────────────────────────────────

RECEPISSEEDA_NOMINAL = """
RÉCÉPISSÉ DE DÉCLARATION D'ACHAT

Enregistré le 15/04/2026

Immatriculation : AB-123-CD
VIN : 1HGBH41JXMN109186
SIRET : 456 789 123 00021
"""


def test_recepisseDA_success():
    r = EXT.extract_from_ocr_text(RECEPISSEEDA_NOMINAL)
    assert r.success is True
    assert r.data["vin"] == "1HGBH41JXMN109186"
    assert r.data["immatriculation"] == "AB-123-CD"
    assert r.data["date_enregistrement"] == "2026-04-15"
    assert r.data["siren_pro"] == "456789123"


def test_recepisseDA_confidence_haute():
    r = EXT.extract_from_ocr_text(RECEPISSEEDA_NOMINAL)
    assert r.confidence >= 0.80


# ── Variante orthographe ──────────────────────────────────────────────────────

RECEPISSE_V2 = """
Recepisse déclaration d'achat
Reçu le 10/03/2026
VIN : WAUZZZ4B21N012345
Immatriculation EF-456-GH
"""


def test_recepisseDA_variante_orthographe():
    r = EXT.extract_from_ocr_text(RECEPISSE_V2)
    assert r.success is True
    assert r.data["vin"] == "WAUZZZ4B21N012345"
    assert r.data["date_enregistrement"] == "2026-03-10"


# ── SIREN déduit du SIRET ─────────────────────────────────────────────────────

def test_recepisseDA_siren_deduit():
    r = EXT.extract_from_ocr_text(RECEPISSEEDA_NOMINAL)
    assert r.data["siren_pro"] == "456789123"


# ── Pas de VIN mais immat présente ───────────────────────────────────────────

RECEPISSE_IMMAT_ONLY = """
Récépissé de déclaration d'achat
Immatriculation : GH-789-IJ
Enregistré le 01/01/2025
"""


def test_recepisseDA_immat_sans_vin():
    r = EXT.extract_from_ocr_text(RECEPISSE_IMMAT_ONLY)
    assert r.success is True
    assert r.data.get("vin") is None
    assert r.data["immatriculation"] == "GH-789-IJ"


# ── Échec document non reconnu ────────────────────────────────────────────────

def test_recepisseDA_inconnu():
    r = EXT.extract_from_ocr_text("Bon de livraison — référence BL-2026-001")
    assert r.success is False
    assert r.confidence <= 0.30


# ── Récépissé sans véhicule ───────────────────────────────────────────────────

RECEPISSE_SANS_VEH = """
Récépissé déclaration d'achat
Enregistré le 15/04/2026
"""


def test_recepisseDA_sans_vehicule():
    r = EXT.extract_from_ocr_text(RECEPISSE_SANS_VEH)
    assert r.success is False
    assert any("VIN" in e or "immatriculat" in e.lower() for e in r.errors)


# ── Date avec format point ────────────────────────────────────────────────────

def test_recepisseDA_date_point():
    ocr = "Récépissé de déclaration d'achat\nEnregistré le 18.04.2026\nVIN : JN1AZNX11Z0000001"
    r = EXT.extract_from_ocr_text(ocr)
    assert r.data["date_enregistrement"] == "2026-04-18"
