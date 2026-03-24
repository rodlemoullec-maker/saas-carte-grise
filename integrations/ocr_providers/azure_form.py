"""
Provider OCR : Azure Form Recognizer (AI Document Intelligence).

Alternative à Google Document AI, performant sur les formulaires
et documents d'identité européens.

Prérequis :
- Azure subscription avec Form Recognizer créé
- AZURE_FORM_ENDPOINT et AZURE_FORM_KEY configurés
"""
from __future__ import annotations

from integrations.ocr_providers.base import BaseOCRProvider, OCRResult


class AzureFormRecognizerProvider(BaseOCRProvider):
    """
    Provider OCR basé sur Azure Form Recognizer.

    TODO: implémenter en utilisant azure-ai-formrecognizer SDK.
    TODO: utiliser le modèle prebuilt-idDocument pour CNI/passeport.
    TODO: mapper la réponse Azure vers OCRResult.
    """

    def __init__(self, endpoint: str, api_key: str) -> None:
        self.endpoint = endpoint
        self.api_key = api_key

    async def process_document(self, file_bytes: bytes, mime_type: str) -> OCRResult:
        # TODO: from azure.ai.formrecognizer import DocumentAnalysisClient
        # TODO: client = DocumentAnalysisClient(endpoint, AzureKeyCredential(api_key))
        # TODO: appel begin_analyze_document + polling + mapping
        raise NotImplementedError
