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


def get_ocr_provider(provider_name: str = "auto") -> BaseOCRProvider:
    """
    Factory pour récupérer le provider OCR selon la configuration.

    Args:
        provider_name: "auto" (défaut), "paddle" ou "tesseract".
            En mode "auto", essaie PaddleOCR en premier et bascule
            automatiquement sur Tesseract si paddlepaddle n'est pas installé.

    Returns:
        Une instance de BaseOCRProvider prête à l'emploi
    """
    import logging
    _log = logging.getLogger(__name__)

    name = provider_name.lower()
    if name == "paddle":
        return PaddleOcrProvider()
    if name == "tesseract":
        return TesseractProvider()
    if name == "auto":
        try:
            import paddle  # noqa: F401 — vérifie la disponibilité
            return PaddleOcrProvider()
        except ModuleNotFoundError:
            _log.info(
                "[OCR] paddlepaddle non disponible — utilisation de Tesseract"
            )
            return TesseractProvider()
    raise ValueError(
        f"Provider OCR inconnu : {provider_name!r}. "
        f"Valeurs supportées : 'auto', 'paddle', 'tesseract'."
    )
