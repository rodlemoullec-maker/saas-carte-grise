"""
Provider OCR : Google Document AI.

Meilleure option pour les documents structurés (COC, CNI, permis)
car il peut être fine-tuné sur des types de documents spécifiques.

Prérequis :
- Projet Google Cloud avec Document AI activé
- GOOGLE_APPLICATION_CREDENTIALS configuré
- Processor ID créé dans la console Google Cloud (region EU recommandée)
"""
from __future__ import annotations

from integrations.ocr_providers.base import BaseOCRProvider, OCRPage, OCRResult


class GoogleDocAIProvider(BaseOCRProvider):
    """
    Provider OCR basé sur Google Document AI.

    TODO: implémenter en utilisant google-cloud-documentai SDK.
    TODO: configurer le processor pour traiter les documents FR.
    TODO: mapper la réponse DocumentAI vers OCRResult.
    TODO: extraire les blocs de texte avec positions (bounding boxes).
    """

    def __init__(self, project_id: str, location: str, processor_id: str) -> None:
        self.project_id = project_id
        self.location = location
        self.processor_id = processor_id

    async def process_document(self, file_bytes: bytes, mime_type: str) -> OCRResult:
        # TODO: from google.cloud import documentai_v1 as documentai
        # TODO: client = documentai.DocumentProcessorServiceClient()
        # TODO: appel process_document + mapping vers OCRResult
        raise NotImplementedError
