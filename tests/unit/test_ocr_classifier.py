"""Tests unitaires — Document classifier."""
from __future__ import annotations

import pytest

from engine.models.documents import DocumentType
from engine.ocr.classifier import DocumentClassifier


class TestDocumentClassifier:

    def setup_method(self):
        self.c = DocumentClassifier()

    def test_cni(self):
        text = "REPUBLIQUE FRANCAISE\nCARTE NATIONALE D'IDENTITE\nNom de naissance: DUPONT\nDate de naissance: 15/05/1990"
        result = self.c.classify(text)
        assert result.doc_type == DocumentType.CNI
        assert result.confidence > 0.5

    def test_permis(self):
        text = "PERMIS DE CONDUIRE\nCatégories: B\nDate de délivrance: 01/06/2010\nPréfet de Paris"
        result = self.c.classify(text)
        assert result.doc_type == DocumentType.PERMIS
        assert result.confidence > 0.5

    def test_coc(self):
        text = "CERTIFICAT DE CONFORMITE\nCOC\nCNIT: AB12345C\nPuissance nette maximale: 110 kW\nHomologation CE"
        result = self.c.classify(text)
        assert result.doc_type == DocumentType.COC
        assert result.confidence > 0.5

    def test_assurance(self):
        text = "ATTESTATION D'ASSURANCE automobile\nResponsabilité Civile\nDate d'effet: 01/01/2026\nCompagnie d'assurance: AXA"
        result = self.c.classify(text)
        assert result.doc_type == DocumentType.ASSURANCE
        assert result.confidence > 0.5

    def test_controle_technique(self):
        text = "CONTROLE TECHNIQUE\nRésultat: Favorable\nCentre de contrôle agréé\nContre-visite non requise"
        result = self.c.classify(text)
        assert result.doc_type == DocumentType.CONTROLE_TECHNIQUE
        assert result.confidence > 0.5

    def test_cerfa_vn(self):
        text = "CERFA 13749 Demande de certificat d'immatriculation véhicule neuf"
        result = self.c.classify(text)
        assert result.doc_type == DocumentType.CERFA_VN
        assert result.confidence > 0.5

    def test_cerfa_cession(self):
        text = "CERFA 15776 DECLARATION DE CESSION vendeur acquéreur"
        result = self.c.classify(text)
        assert result.doc_type == DocumentType.CERFA_CESSION
        assert result.confidence > 0.5

    def test_kbis(self):
        text = "EXTRAIT DU REGISTRE du Commerce et des Sociétés\nGreffe du tribunal\nKBIS"
        result = self.c.classify(text)
        assert result.doc_type == DocumentType.KBIS
        assert result.confidence > 0.5

    def test_empty_text_low_confidence(self):
        result = self.c.classify("")
        assert result.confidence < 0.1
