"""Tests unitaires — MandatExtractor (Cerfa 13757)."""
import pytest
from engine.extractors.mandat import MandatExtractor

EXT = MandatExtractor()


# ── Cas nominal ───────────────────────────────────────────────────────────────

MANDAT_NOMINAL = """
MANDAT DE VENTE
Cerfa n° 13757*02

Je soussigné, Mandant : DUPONT Jean-Paul
autorise, Mandataire : GARAGE AUTO PLUS SARL
SIRET : 789 012 345 00015

à effectuer toutes les démarches nécessaires à la vente du véhicule :
Immatriculation : CD-456-EF
VIN : WAUZZZ4B21N012345

Fait le 15/04/2026
[signature] mandant
"""


def test_mandat_success():
    r = EXT.extract_from_ocr_text(MANDAT_NOMINAL)
    assert r.success is True
    assert r.data["vin"] == "WAUZZZ4B21N012345"
    assert r.data["immatriculation"] == "CD-456-EF"


def test_mandat_mandant():
    r = EXT.extract_from_ocr_text(MANDAT_NOMINAL)
    assert r.data["mandant_nom"] == "DUPONT"


def test_mandat_siret():
    r = EXT.extract_from_ocr_text(MANDAT_NOMINAL)
    assert r.data["mandataire_siret"] == "78901234500015"


def test_mandat_date():
    r = EXT.extract_from_ocr_text(MANDAT_NOMINAL)
    assert r.data["date_mandat"] == "2026-04-15"


def test_mandat_signature():
    r = EXT.extract_from_ocr_text(MANDAT_NOMINAL)
    assert r.data["signature_mandant"] is True


def test_mandat_confidence():
    r = EXT.extract_from_ocr_text(MANDAT_NOMINAL)
    assert r.confidence >= 0.80


# ── Procuration (variante) ────────────────────────────────────────────────────

PROCURATION = """
PROCURATION DE VENTE VÉHICULE

Je soussigné MARTIN Sophie, propriétaire
autorise le professionnel GARAGE DU NORD à vendre mon véhicule.
Immatriculation : GH-789-IJ
VIN : 1HGBH41JXMN109186
Fait le 10/04/2026
"""


def test_procuration_detecte():
    r = EXT.extract_from_ocr_text(PROCURATION)
    assert r.success is True


# ── Signature manquante (MISSING/BLANK) ──────────────────────────────────────

MANDAT_NON_SIGNE = """
Mandat de vente Cerfa 13757
Mandant : BERNARD Michel
Immatriculation : KL-012-MN
VIN : JN1AZNX11Z0000001
[MISSING/BLANK]
"""


def test_mandat_sans_signature():
    r = EXT.extract_from_ocr_text(MANDAT_NON_SIGNE)
    assert r.data["signature_mandant"] is False


# ── Échec sans véhicule ───────────────────────────────────────────────────────

MANDAT_SANS_VEH = """
Mandat Cerfa 13757
Mandant : DUPONT Jean
"""


def test_mandat_sans_vehicule():
    r = EXT.extract_from_ocr_text(MANDAT_SANS_VEH)
    assert r.success is False


# ── Document non reconnu ──────────────────────────────────────────────────────

def test_mandat_inconnu():
    r = EXT.extract_from_ocr_text("Acte de vente immobilier — Paris 2026")
    assert r.success is False
    assert r.confidence <= 0.25


# ── Date avec format point ────────────────────────────────────────────────────

def test_mandat_date_point():
    ocr = "Mandat de vente\nMandant : TEST Pierre\nImmat : OP-345-QR\nVIN : 1HGBH41JXMN109186\nFait le 18.04.2026"
    r = EXT.extract_from_ocr_text(ocr)
    assert r.data["date_mandat"] == "2026-04-18"
