"""Tests unitaires — CertificatCessionExtractor (Cerfa 15776 tamponné pro)."""
import pytest
from engine.extractors.certificat_cession import CertificatCessionExtractor

EXT = CertificatCessionExtractor()


# ── Cas nominal avec tampon ───────────────────────────────────────────────────

CERT_NOMINAL = """
CERTIFICAT DE CESSION
Cerfa 15776*02

Vendeur : AUTO PREMIUM SARL
SIRET : 456 789 123 00021
Acquéreur : MARTIN Sophie
VIN : 1HGBH41JXMN109186
Immatriculation : AB-123-CD
Date de cession : 15/04/2026

[signature] vendeur
[SIGNÉE] acheteur
[cachet] pro SIRET : 456 789 123 00021
"""


def test_cert_success():
    r = EXT.extract_from_ocr_text(CERT_NOMINAL)
    assert r.success is True
    assert r.data["vin"] == "1HGBH41JXMN109186"
    assert r.data["immatriculation"] == "AB-123-CD"


def test_cert_numero_cerfa():
    r = EXT.extract_from_ocr_text(CERT_NOMINAL)
    assert r.data["numero_cerfa"] == "15776"


def test_cert_vendeur():
    r = EXT.extract_from_ocr_text(CERT_NOMINAL)
    assert r.data.get("vendeur_nom") is not None


def test_cert_siret():
    r = EXT.extract_from_ocr_text(CERT_NOMINAL)
    assert r.data["vendeur_siret"] == "45678912300021"


def test_cert_acheteur():
    r = EXT.extract_from_ocr_text(CERT_NOMINAL)
    assert r.data.get("acheteur_nom") is not None


def test_cert_date():
    r = EXT.extract_from_ocr_text(CERT_NOMINAL)
    assert r.data["date_cession"] == "2026-04-15"


def test_cert_tampon():
    r = EXT.extract_from_ocr_text(CERT_NOMINAL)
    assert r.data["tampon_pro"] is True


def test_cert_confidence_haute():
    r = EXT.extract_from_ocr_text(CERT_NOMINAL)
    assert r.confidence >= 0.85


# ── Certificat sans tampon → confiance réduite, erreur signalée ──────────────

CERT_SANS_TAMPON = """
Certificat de Cession 15776
Vendeur : DUPONT Jean
Acquéreur : MARTIN Pierre
VIN : WAUZZZ4B21N012345
Date cession : 01/01/2025
[signature]
"""


def test_cert_sans_tampon():
    r = EXT.extract_from_ocr_text(CERT_SANS_TAMPON)
    assert r.data["tampon_pro"] is False
    assert any("cachet" in e.lower() or "tampon" in e.lower() for e in r.errors)
    assert r.confidence < 0.80


# ── Détection via "Déclaration de cession" ───────────────────────────────────

CERT_DECL = """
DÉCLARATION DE CESSION DE VÉHICULE
Cerfa n° 15776
Cédant : LEROY Marc
VIN : JN1AZNX11Z0000001
SIRET : 123456789 00011
[tampon]
"""


def test_cert_declaration_cession():
    r = EXT.extract_from_ocr_text(CERT_DECL)
    assert r.success is True
    assert r.data["tampon_pro"] is True


# ── Document non reconnu ──────────────────────────────────────────────────────

def test_cert_inconnu():
    r = EXT.extract_from_ocr_text("Facture EDF — Consommation électrique")
    assert r.success is False
    assert r.confidence <= 0.25


# ── Immatriculation sans VIN ──────────────────────────────────────────────────

CERT_IMMAT_ONLY = """
Certificat de Cession 15776
Immatriculation : GH-789-IJ
Vendeur : TEST SARL
Date : 18/04/2026
[tampon] SIRET : 999888777 00055
"""


def test_cert_immat_sans_vin():
    r = EXT.extract_from_ocr_text(CERT_IMMAT_ONLY)
    assert r.success is True
    assert r.data.get("vin") is None
    assert r.data["immatriculation"] == "GH-789-IJ"
