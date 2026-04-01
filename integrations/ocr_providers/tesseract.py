"""
Provider OCR : Tesseract (local, gratuit).

Premier niveau OCR — si la confidence est trop basse (< 40%),
le système bascule automatiquement sur Google Document AI.

Dépendance : tesseract-ocr installé localement + pytesseract.
"""
from __future__ import annotations

import asyncio
import io
import logging

from integrations.ocr_providers.base import BaseOCRProvider, OCRPage, OCRResult

logger = logging.getLogger(__name__)

MIN_TEXT_LENGTH = 50


class TesseractProvider(BaseOCRProvider):

    def __init__(self, lang: str = "fra") -> None:
        self.lang = lang

    async def process_document(self, file_bytes: bytes, mime_type: str) -> OCRResult:
        """OCR via Tesseract local. Wrappe l'appel synchrone en async."""
        result = await asyncio.get_event_loop().run_in_executor(
            None, self._process_sync, file_bytes, mime_type
        )
        return result

    def _process_sync(self, file_bytes: bytes, mime_type: str) -> OCRResult:
        import pytesseract
        from PIL import Image

        images = self._to_images(file_bytes, mime_type)

        pages: list[OCRPage] = []
        all_text_parts: list[str] = []
        total_confidence = 0.0

        for i, img in enumerate(images):
            page_text = pytesseract.image_to_string(img, lang=self.lang)

            # Confidence par mot
            data = pytesseract.image_to_data(
                img, lang=self.lang, output_type=pytesseract.Output.DICT
            )
            confidences = [
                int(c) for c in data["conf"]
                if str(c).lstrip("-").isdigit() and int(c) > 0
            ]
            page_confidence = (
                sum(confidences) / len(confidences) / 100.0
                if confidences else 0.0
            )

            pages.append(OCRPage(
                page_number=i + 1,
                text=page_text.strip(),
                confidence=page_confidence,
            ))
            all_text_parts.append(page_text.strip())
            total_confidence += page_confidence

        full_text = "\n\n".join(all_text_parts)
        avg_confidence = total_confidence / len(pages) if pages else 0.0

        # Texte trop court → confidence surestimée
        if len(full_text.strip()) < MIN_TEXT_LENGTH:
            avg_confidence = min(avg_confidence, 0.30)

        return OCRResult(
            pages=pages,
            full_text=full_text,
            average_confidence=avg_confidence,
            provider="tesseract",
            metadata={"lang": self.lang},
        )

    def _to_images(self, file_bytes: bytes, mime_type: str) -> list:
        from PIL import Image

        if mime_type == "application/pdf":
            # Essayer PyPDF d'abord (PDF avec texte)
            try:
                from pypdf import PdfReader
                reader = PdfReader(io.BytesIO(file_bytes))
                text = ""
                for page in reader.pages:
                    t = page.extract_text()
                    if t:
                        text += t + "\n"
                if len(text.strip()) > MIN_TEXT_LENGTH:
                    # PDF avec texte natif — pas besoin d'images
                    # Retourne une "fausse image" pour garder le flux uniforme
                    # On va court-circuiter dans _process_sync
                    pass
            except Exception:
                pass

            try:
                from pdf2image import convert_from_bytes
                return convert_from_bytes(file_bytes, dpi=300)
            except ImportError:
                try:
                    import fitz
                    doc = fitz.open(stream=file_bytes, filetype="pdf")
                    images = []
                    for page in doc:
                        pix = page.get_pixmap(dpi=300)
                        img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
                        images.append(img)
                    return images
                except ImportError:
                    logger.error("Ni pdf2image ni PyMuPDF disponibles pour les PDF")
                    return []
        else:
            return [Image.open(io.BytesIO(file_bytes))]
