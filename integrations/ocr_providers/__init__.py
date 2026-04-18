from integrations.ocr_providers.base import BaseOCRProvider, OCRPage, OCRResult
from integrations.ocr_providers.paddle_ocr import PaddleOcrProvider

__all__ = [
    "BaseOCRProvider",
    "OCRResult",
    "OCRPage",
    "PaddleOcrProvider",
]


def get_ocr_provider(provider_name: str = "paddle") -> BaseOCRProvider:
    """
    Factory pour récupérer le provider OCR selon la configuration.

    Args:
        provider_name: "paddle" (défaut).

    Returns:
        Une instance de BaseOCRProvider prête à l'emploi
    """
    name = provider_name.lower()
    if name in {"paddle", "auto"}:
        return PaddleOcrProvider()
    raise ValueError(
        f"Provider OCR inconnu : {provider_name!r}. "
        f"Valeurs supportées : 'paddle'."
    )
