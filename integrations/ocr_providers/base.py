"""
Interface abstraite pour les providers OCR.

Permet de switcher entre Google Document AI, Azure Form Recognizer
ou Tesseract sans changer le code appelant.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field


@dataclass
class OCRPage:
    page_number: int
    text: str
    confidence: float
    blocks: list[dict] = field(default_factory=list)  # Blocs de texte avec positions


@dataclass
class OCRResult:
    pages: list[OCRPage]
    full_text: str
    average_confidence: float
    provider: str
    metadata: dict = field(default_factory=dict)


class BaseOCRProvider(ABC):

    @abstractmethod
    async def process_document(self, file_bytes: bytes, mime_type: str) -> OCRResult:
        """
        Envoie un document au provider OCR et retourne le texte extrait.

        Args:
            file_bytes: Contenu brut du fichier (PDF, JPG, PNG...)
            mime_type: Type MIME du fichier

        Returns:
            OCRResult avec le texte extrait et les scores de confiance
        """
        ...

    def preprocess_image(self, file_bytes: bytes) -> bytes:
        """
        Prétraitement optionnel de l'image avant OCR :
        - Correction d'orientation (deskew)
        - Débruitage
        - Amélioration contraste
        - Normalisation résolution à 300 DPI

        TODO: implémenter avec Pillow / OpenCV.
        """
        return file_bytes
