"""Tests unitaires — CNIHebergeantExtractor."""
import pytest
from engine.extractors.cni_hebergeant import CNIHebergeantExtractor

EXT = CNIHebergeantExtractor()


# ── Cas nominal CNI française ─────────────────────────────────────────────────

CNI_NOMINALE = """
CARTE NATIONALE D'IDENTITÉ
REPUBLIQUE FRANÇAISE

NOM : MARTIN
PRÉNOM : JEAN-PIERRE
Né le 05/06/1975 à PARIS
Nationalité : FRANÇAISE
N° : 123456789012
Valable jusqu'au 01/01/2035
"""


def test_cni_success():
    r = EXT.extract_from_ocr_text(CNI_NOMINALE)
    assert r.success is True
    assert r.data["nom"] == "MARTIN"
    assert r.data["prenom"] == "JEAN-PIERRE"


def test_cni_date_naissance():
    r = EXT.extract_from_ocr_text(CNI_NOMINALE)
    assert r.data["date_naissance"] == "1975-06-05"


def test_cni_numero():
    r = EXT.extract_from_ocr_text(CNI_NOMINALE)
    assert r.data["numero_document"] == "123456789012"


def test_cni_date_expiration():
    r = EXT.extract_from_ocr_text(CNI_NOMINALE)
    assert r.data["date_expiration"] == "2035-01-01"


def test_cni_nationalite_defaut():
    r = EXT.extract_from_ocr_text(CNI_NOMINALE)
    assert r.data["nationalite"] == "FRANÇAISE"


def test_cni_confidence():
    r = EXT.extract_from_ocr_text(CNI_NOMINALE)
    assert r.confidence >= 0.85


# ── Passeport ────────────────────────────────────────────────────────────────

PASSEPORT = """
PASSEPORT
FRANCE

Nom : DUPONT
Prénom : SOPHIE
Née le 10/12/1990 à LYON
N° : AB1234567
Expire le 15/03/2030
"""


def test_passeport_success():
    r = EXT.extract_from_ocr_text(PASSEPORT)
    assert r.success is True
    assert r.data["nom"] == "DUPONT"


def test_passeport_numero():
    r = EXT.extract_from_ocr_text(PASSEPORT)
    assert r.data["numero_document"] == "AB1234567"


# ── CNI sans numéro → confiance réduite ──────────────────────────────────────

CNI_SANS_NUM = """
CARTE NATIONALE D'IDENTITÉ
NOM : BERNARD
PRÉNOM : MICHEL
Né le 20/08/1965 à MARSEILLE
"""


def test_cni_sans_numero_confidence():
    r = EXT.extract_from_ocr_text(CNI_SANS_NUM)
    assert r.success is True
    assert 0.65 <= r.confidence <= 0.80


# ── Document non reconnu ──────────────────────────────────────────────────────

def test_cni_inconnu():
    r = EXT.extract_from_ocr_text("Attestation d'hébergement — 15 Rue de la Paix")
    assert r.success is False
    assert r.confidence <= 0.25


# ── Lieu de naissance ─────────────────────────────────────────────────────────

def test_cni_lieu_naissance():
    r = EXT.extract_from_ocr_text(CNI_NOMINALE)
    assert r.data.get("lieu_naissance") is not None
    assert "PARIS" in r.data["lieu_naissance"]


# ── CNI identity card (label en anglais) ─────────────────────────────────────

CNI_EN = """
IDENTITY CARD
NOM / NAME : LEROY
PRÉNOMS / GIVEN NAMES : CLAIRE
Date de naissance : 15/07/1988
Nationalité : FRANÇAISE
N° 987654321098
"""


def test_cni_label_anglais():
    r = EXT.extract_from_ocr_text(CNI_EN)
    assert r.success is True
    assert r.data["nom"] == "LEROY"
