"""
Interface abstraite pour les providers OCR.

Permet de switcher entre Google Document AI, Azure Form Recognizer
ou Tesseract sans changer le code appelant.
"""
from __future__ import annotations

import io
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


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

    def preprocess_image(self, file_bytes: bytes, mime_type: str = "") -> bytes:
        """
        Prétraitement de l'image avant OCR :
        - Conversion en niveaux de gris
        - Amélioration du contraste (CLAHE)
        - Normalisation résolution (redimensionne si trop petit)

        Ne s'applique qu'aux images (JPEG, PNG, TIFF, WEBP), pas aux PDF.
        """
        # Ne pas toucher aux PDF
        if "pdf" in mime_type.lower():
            return file_bytes

        try:
            from PIL import Image, ImageEnhance, ImageFilter

            img = Image.open(io.BytesIO(file_bytes))

            # Convertir en RGB si necessaire (RGBA, palette, etc.)
            if img.mode not in ("RGB", "L"):
                img = img.convert("RGB")

            # Si l'image est trop petite, agrandir (ameliore l'OCR)
            min_dim = 1500
            w, h = img.size
            if max(w, h) < min_dim:
                scale = min_dim / max(w, h)
                img = img.resize((int(w * scale), int(h * scale)), Image.LANCZOS)
                logger.debug(f"[Preprocess] Image agrandie {w}x{h} → {img.size[0]}x{img.size[1]}")

            # Convertir en niveaux de gris
            img = img.convert("L")

            # Ameliorer le contraste
            enhancer = ImageEnhance.Contrast(img)
            img = enhancer.enhance(1.5)

            # Ameliorer la nettete
            enhancer = ImageEnhance.Sharpness(img)
            img = enhancer.enhance(1.3)

            # Sauvegarder en PNG (meilleur pour l'OCR que JPEG)
            buf = io.BytesIO()
            img.save(buf, format="PNG", optimize=True)
            result = buf.getvalue()
            logger.debug(f"[Preprocess] {len(file_bytes)} → {len(result)} bytes")
            return result

        except Exception as e:
            logger.warning(f"[Preprocess] Echec preprocessing, envoi original: {e}")
            return file_bytes
