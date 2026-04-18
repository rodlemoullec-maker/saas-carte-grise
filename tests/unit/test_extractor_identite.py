"""
Tests unitaires — IdentiteExtractor.

Valide l'extraction par regex/MRZ sur des textes OCR synthétiques
représentant une CNI française et un passeport français.
Aucun appel OCR réel, aucun LLM.
"""
from __future__ import annotations

import pytest
from engine.extractors.identite import IdentiteExtractor


@pytest.fixture
def extractor() -> IdentiteExtractor:
    return IdentiteExtractor()


# ─── Textes OCR synthétiques ──────────────────────────────────────────────────

CNI_OCR = """\
CARTE NATIONALE D'IDENTITE
Nom/Surname (1)
MARTIN
Prénoms/Given names (2)
JEAN PIERRE
Date de naissance 15.04.1985
Lieu de naissance LYON
Date de délivrance/ Date of issue
12 01 2020
Date d'expiration/ Date of expiry
12 01 2035
No 123456789012
Nationalité FRANÇAISE
MARTIN<<JEAN<PIERRE<<<<<<<
"""

PASSEPORT_OCR = """\
PASSEPORT / PASSPORT
Date de naissance 23.07.1990
Lieu de naissance BORDEAUX
Sexe/Sex F
Date d'expiration 23.07.2030
No 12AB34567
Nationalité FRA
P<FRADUPONT<<MARIE<CLAIRE<<<<<<<<<<<<<<<<<
"""

CNI_OCR_INCOMPLET = """\
CARTE NATIONALE D'IDENTITE
Prénoms/Given names
SOPHIE
Date d'expiration/ Date of expiry
01 01 2028
"""


# ─── Tests CNI ────────────────────────────────────────────────────────────────

class TestIdentiteExtractorCNI:

    def test_extraction_succes(self, extractor):
        result = extractor.extract(CNI_OCR)
        assert result.success is True

    def test_nom_extrait(self, extractor):
        result = extractor.extract(CNI_OCR)
        assert result.data["nom_naissance"] == "MARTIN"

    def test_prenom_extrait(self, extractor):
        result = extractor.extract(CNI_OCR)
        assert "JEAN" in result.data["prenoms"]

    def test_date_naissance_extraite(self, extractor):
        result = extractor.extract(CNI_OCR)
        assert result.data["date_naissance"] == "1985-04-15"

    def test_date_expiration_extraite(self, extractor):
        result = extractor.extract(CNI_OCR)
        assert result.data["date_expiration"] == "2035-01-12"

    def test_type_document_cni(self, extractor):
        result = extractor.extract(CNI_OCR)
        assert result.data["type_document"] == "CNI"

    def test_lieu_naissance_extrait(self, extractor):
        result = extractor.extract(CNI_OCR)
        assert result.data["lieu_naissance"] == "LYON"

    def test_departement_deduit(self, extractor):
        result = extractor.extract(CNI_OCR)
        assert result.data["departement_naissance"] == "69"

    def test_sexe_deduit_du_prenom(self, extractor):
        result = extractor.extract(CNI_OCR)
        assert result.data["sexe"] == "M"

    def test_confidence_non_nulle(self, extractor):
        result = extractor.extract(CNI_OCR)
        assert result.confidence > 0


# ─── Tests Passeport ─────────────────────────────────────────────────────────

class TestIdentiteExtractorPasseport:

    def test_extraction_succes(self, extractor):
        result = extractor.extract(PASSEPORT_OCR)
        assert result.success is True

    def test_nom_extrait(self, extractor):
        result = extractor.extract(PASSEPORT_OCR)
        assert result.data["nom_naissance"] == "DUPONT"

    def test_type_document_passeport(self, extractor):
        result = extractor.extract(PASSEPORT_OCR)
        assert result.data["type_document"] == "PASSEPORT"

    def test_sexe_explicite(self, extractor):
        result = extractor.extract(PASSEPORT_OCR)
        assert result.data["sexe"] == "F"

    def test_date_naissance_extraite(self, extractor):
        result = extractor.extract(PASSEPORT_OCR)
        assert result.data["date_naissance"] == "1990-07-23"

    def test_date_expiration_extraite(self, extractor):
        result = extractor.extract(PASSEPORT_OCR)
        assert result.data["date_expiration"] == "2030-07-23"

    def test_mrz_booste_confidence(self, extractor):
        result = extractor.extract(PASSEPORT_OCR)
        # La MRZ donne une confidence de 0.8
        assert result.confidence >= 0.8


# ─── Tests cas d'échec ────────────────────────────────────────────────────────

class TestIdentiteExtractorEchec:

    def test_champs_obligatoires_manquants(self, extractor):
        """Sans nom ni date de naissance → échec."""
        result = extractor.extract(CNI_OCR_INCOMPLET)
        assert result.success is False

    def test_erreur_renseignee(self, extractor):
        result = extractor.extract(CNI_OCR_INCOMPLET)
        assert len(result.errors) > 0

    def test_texte_vide(self, extractor):
        result = extractor.extract("")
        assert result.success is False
