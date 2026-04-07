from integrations.ocr_providers.base import BaseOCRProvider, OCRPage, OCRResult
from integrations.ocr_providers.paddle_ocr import PaddleOcrProvider
from integrations.ocr_providers.tesseract import TesseractProvider

__all__ = [
    "BaseOCRProvider",
    "OCRResult",
    "OCRPage",
    "PaddleOcrProvider",
    "TesseractProvider",
]


def get_ocr_provider(provider_name: str = "paddle") -> BaseOCRProvider:
    """
    Factory pour récupérer le provider OCR selon la configuration.

    Args:
        provider_name: "paddle" (défaut) ou "tesseract" (fallback léger)

    Returns:
        Une instance de BaseOCRProvider prête à l'emploi
    """
    name = provider_name.lower()
    if name == "paddle":
        return PaddleOcrProvider()
    if name == "tesseract":
        return TesseractProvider()
    raise ValueError(
        f"Provider OCR inconnu : {provider_name!r}. "
        f"Valeurs supportées : 'paddle', 'tesseract'."
    )
