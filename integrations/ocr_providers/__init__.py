from integrations.ocr_providers.azure_form import AzureFormRecognizerProvider
from integrations.ocr_providers.base import BaseOCRProvider, OCRPage, OCRResult
from integrations.ocr_providers.google_docai import GoogleDocAIProvider

__all__ = [
    "BaseOCRProvider", "OCRResult", "OCRPage",
    "GoogleDocAIProvider", "AzureFormRecognizerProvider",
]
