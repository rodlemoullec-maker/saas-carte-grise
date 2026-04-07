"""
Provider OCR PaddleOCR — local, gratuit, open source.

PaddleOCR remplace Google Document AI dans la version locale d'Imatra.
Tout tourne sur la machine de l'agent, aucun appel cloud.

Précision en français : ~90-93% sur documents standards (CNI, factures, etc.).
Le pré-traitement d'image (héritage de BaseOCRProvider) améliore encore les résultats.

Au premier appel, PaddleOCR télécharge automatiquement les modèles français
pré-entraînés (~100 Mo). Ils sont mis en cache dans ~/.paddleocr/.
"""
from __future__ import annotations

import io
import logging
import tempfile
from typing import TYPE_CHECKING

from integrations.ocr_providers.base import BaseOCRProvider, OCRPage, OCRResult

if TYPE_CHECKING:
    from paddleocr import PaddleOCR

logger = logging.getLogger(__name__)


class PaddleOcrProvider(BaseOCRProvider):
    """
    Provider OCR utilisant PaddleOCR en local.

    Singleton interne : le modèle PaddleOCR est lourd à charger (1-2 secondes),
    on l'instancie une seule fois et on le réutilise pour tous les documents.
    """

    _ocr_instance: "PaddleOCR | None" = None

    def __init__(self, language: str = "fr", use_gpu: bool = False):
        self.language = language
        self.use_gpu = use_gpu

    @classmethod
    def _get_ocr(cls, language: str, use_gpu: bool) -> "PaddleOCR":
        """Lazy init du modèle PaddleOCR (singleton)."""
        if cls._ocr_instance is None:
            try:
                from paddleocr import PaddleOCR
            except ImportError as e:
                raise ImportError(
                    "PaddleOCR n'est pas installé. "
                    "Installez avec: pip install paddleocr paddlepaddle"
                ) from e

            logger.info(f"[PaddleOCR] Chargement du modèle (langue={language}, gpu={use_gpu})")
            cls._ocr_instance = PaddleOCR(
                use_angle_cls=True,
                lang=language,
                use_gpu=use_gpu,
                show_log=False,
            )
            logger.info("[PaddleOCR] Modèle chargé")
        return cls._ocr_instance

    async def process_document(self, file_bytes: bytes, mime_type: str) -> OCRResult:
        """
        Lit un document avec PaddleOCR et retourne le texte extrait + scores.

        Args:
            file_bytes: contenu binaire du fichier
            mime_type: type MIME du fichier

        Returns:
            OCRResult avec une page (PaddleOCR ne sépare pas par pages PDF —
            on traite chaque page séparément si PDF multi-pages, voir _split_pdf)
        """
        # Pré-traitement (héritage)
        processed_bytes = self.preprocess_image(file_bytes, mime_type)

        # PDF multi-pages : convertir en images puis OCR page par page
        if "pdf" in mime_type.lower():
            return await self._process_pdf(processed_bytes)

        # Image directe
        return await self._process_image(processed_bytes, page_number=1)

    async def _process_pdf(self, file_bytes: bytes) -> OCRResult:
        """Convertit chaque page du PDF en image et appelle PaddleOCR."""
        try:
            from pdf2image import convert_from_bytes
        except ImportError as e:
            raise ImportError(
                "pdf2image n'est pas installé. "
                "Installez avec: pip install pdf2image"
            ) from e

        images = convert_from_bytes(file_bytes, dpi=200)
        pages: list[OCRPage] = []

        for i, img in enumerate(images, start=1):
            buf = io.BytesIO()
            img.save(buf, format="PNG")
            page_result = await self._process_image(buf.getvalue(), page_number=i)
            pages.extend(page_result.pages)

        full_text = "\n\n".join(p.text for p in pages)
        avg_conf = (
            sum(p.confidence for p in pages) / len(pages) if pages else 0.0
        )
        return OCRResult(
            pages=pages,
            full_text=full_text,
            average_confidence=avg_conf,
            provider="paddle",
            metadata={"page_count": len(pages)},
        )

    async def _process_image(self, image_bytes: bytes, page_number: int = 1) -> OCRResult:
        """Traite une image unique avec PaddleOCR."""
        ocr = self._get_ocr(self.language, self.use_gpu)

        # PaddleOCR accepte un chemin de fichier ou un numpy array
        # On passe par un fichier temporaire pour rester simple et compatible
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
            tmp.write(image_bytes)
            tmp_path = tmp.name

        try:
            result = ocr.ocr(tmp_path, cls=True)
        finally:
            import os
            try:
                os.unlink(tmp_path)
            except OSError:
                pass

        # PaddleOCR retourne : [[bbox, (text, confidence)], ...]
        # ou une liste vide si rien détecté
        blocks = []
        text_lines = []
        confidences = []

        if result and result[0]:
            for line in result[0]:
                bbox = line[0]
                text, conf = line[1]
                text_lines.append(text)
                confidences.append(conf)
                blocks.append({
                    "text": text,
                    "confidence": conf,
                    "bbox": bbox,  # 4 points (x, y)
                })

        full_text = "\n".join(text_lines)
        avg_confidence = sum(confidences) / len(confidences) if confidences else 0.0

        page = OCRPage(
            page_number=page_number,
            text=full_text,
            confidence=avg_confidence,
            blocks=blocks,
        )

        return OCRResult(
            pages=[page],
            full_text=full_text,
            average_confidence=avg_confidence,
            provider="paddle",
            metadata={
                "language": self.language,
                "blocks_count": len(blocks),
            },
        )
