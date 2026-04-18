"""Tests unitaires — CGBarreeExtractor."""
import pytest
from engine.extractors.cg_barree import CGBarreeExtractor

EXT = CGBarreeExtractor()


# ── Cas nominal ───────────────────────────────────────────────────────────────

CG_NOMINALE = """
CERTIFICAT D'IMMATRICULATION
Immatriculation : AB-123-CD
VIN : 1HGBH41JXMN109186
Titulaire : MARTIN Sophie
Mise en circulation : 12/03/2019
Marque : PEUGEOT
Genre : VP
Numéro de formule : 12345678901

VENDU LE 15/04/2026 À 14:30
Vendu à DUPONT Jean-Pierre
[signature] vendeur
"""


def test_cg_nominale_success():
    r = EXT.extract_from_ocr_text(CG_NOMINALE)
    assert r.success is True
    assert r.data["vin"] == "1HGBH41JXMN109186"
    assert r.data["immatriculation"] == "AB-123-CD"
    assert r.data["date_vente"] == "2026-04-15"
    assert r.data["heure_vente"] == "14:30"
    assert r.confidence >= 0.80


def test_cg_barre_diagonale():
    r = EXT.extract_from_ocr_text(CG_NOMINALE)
    assert r.data["barre_diagonale"] is True


def test_cg_titulaire():
    r = EXT.extract_from_ocr_text(CG_NOMINALE)
    assert r.data["titulaire_nom"] == "MARTIN"
    assert r.data["titulaire_prenom"] == "Sophie"


def test_cg_acheteur_barre():
    r = EXT.extract_from_ocr_text(CG_NOMINALE)
    assert r.data["acheteur_nom_barre"] == "DUPONT"
    assert "Jean" in r.data.get("acheteur_prenom_barre", "")


def test_cg_n_formule():
    r = EXT.extract_from_ocr_text(CG_NOMINALE)
    assert r.data["n_formule"] == "12345678901"


# ── Immatriculation ancienne format (pré-2009) ────────────────────────────────

CG_ANCIENNE = """
Immatriculation : 1234 TZ 75
VIN : JN1AZNX11Z0000001
Vendu le 10/04/2026 à 09h00
[signature]
"""


def test_cg_ancienne_format():
    # Ancien format ne correspond pas à notre regex SIV → success dépend du VIN
    r = EXT.extract_from_ocr_text(CG_ANCIENNE)
    assert r.data.get("vin") == "JN1AZNX11Z0000001"
    assert r.data["date_vente"] == "2026-04-10"


# ── Heure au format 09h00 ─────────────────────────────────────────────────────

def test_heure_format_h():
    ocr = "Vendu le 18/04/2026 à 09h45\nVIN : 1HGBH41JXMN109186"
    r = EXT.extract_from_ocr_text(ocr)
    assert r.data["heure_vente"] == "09:45"


# ── Échec si pas de date de vente ─────────────────────────────────────────────

CG_SANS_VENTE = """
Immatriculation : EF-456-GH
VIN : WAUZZZ4B21N012345
Titulaire : LEFEBVRE Marc
"""


def test_cg_sans_vente_failure():
    r = EXT.extract_from_ocr_text(CG_SANS_VENTE)
    assert r.success is False
    assert any("vente" in e.lower() for e in r.errors)


# ── Document vide / non pertinent ────────────────────────────────────────────

def test_cg_vide():
    r = EXT.extract_from_ocr_text("Lorem ipsum dolor sit amet.")
    assert r.success is False
    assert r.confidence < 0.50


# ── Confiance correcte ────────────────────────────────────────────────────────

def test_cg_confidence_vin_vente():
    r = EXT.extract_from_ocr_text(CG_NOMINALE)
    assert r.confidence == 0.85


def test_cg_confidence_immat_seulement():
    ocr = "Immatriculation : CD-789-EF\nVendu le 01/01/2025\n[signature]"
    r = EXT.extract_from_ocr_text(ocr)
    assert r.confidence == 0.60


# ── Format de date avec point ─────────────────────────────────────────────────

def test_cg_date_point():
    ocr = "VIN : 1HGBH41JXMN109186\nVendu le 15.04.2026 à 10:00"
    r = EXT.extract_from_ocr_text(ocr)
    assert r.data["date_vente"] == "2026-04-15"


# ── Marque et genre ───────────────────────────────────────────────────────────

def test_cg_marque_genre():
    r = EXT.extract_from_ocr_text(CG_NOMINALE)
    assert r.data.get("marque") is not None
    assert r.data.get("genre_national") is not None
