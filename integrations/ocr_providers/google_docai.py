"""
Provider OCR : Google Document AI.

Credentials : gen-lang-client-0123501972-a55d0eeea7d2.json
Project : 275852582765
Processor : 6a6fede4a9a9caf1
Region : eu
"""
from __future__ import annotations

import logging
import os

from integrations.ocr_providers.base import BaseOCRProvider, OCRPage, OCRResult

logger = logging.getLogger(__name__)


class GoogleDocAIProvider(BaseOCRProvider):

    def __init__(
        self,
        project_id: str = "275852582765",
        location: str = "eu",
        processor_id: str = "6a6fede4a9a9caf1",
        credentials_path: str | None = None,
    ) -> None:
        self.project_id = project_id
        self.location = location
        self.processor_id = processor_id
        if credentials_path:
            os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = credentials_path

    async def process_document(self, file_bytes: bytes, mime_type: str) -> OCRResult:
        """Envoie un document a Google Document AI et retourne le texte extrait."""
        import asyncio

        # Preprocessing images (contraste, nettete, redimensionnement)
        processed_bytes = self.preprocess_image(file_bytes, mime_type)
        # Si preprocesse en PNG, mettre a jour le mime_type
        processed_mime = "image/png" if processed_bytes != file_bytes else mime_type

        result = await asyncio.get_event_loop().run_in_executor(
            None, self._process_sync, processed_bytes, processed_mime
        )
        return result

    def process_sync(self, file_bytes: bytes, mime_type: str) -> OCRResult:
        """Version synchrone pour usage direct."""
        return self._process_sync(file_bytes, mime_type)

    def _process_sync(self, file_bytes: bytes, mime_type: str) -> OCRResult:
        from google.cloud import documentai_v1 as documentai

        opts = {}
        if self.location == "eu":
            opts = {"api_endpoint": "eu-documentai.googleapis.com"}
        client = documentai.DocumentProcessorServiceClient(client_options=opts)
        resource_name = client.processor_path(
            self.project_id, self.location, self.processor_id
        )

        raw_document = documentai.RawDocument(content=file_bytes, mime_type=mime_type)
        request = documentai.ProcessRequest(name=resource_name, raw_document=raw_document)

        logger.info(f"Document AI: envoi {len(file_bytes)} bytes ({mime_type})")
        response = client.process_document(request=request)
        document = response.document

        # Mapper vers OCRResult
        pages = []
        for i, page in enumerate(document.pages):
            page_text = ""
            confidence_sum = 0.0
            count = 0
            blocks = []

            for block in page.blocks:
                block_text = self._get_text(block.layout, document.text)
                conf = block.layout.confidence if block.layout.confidence else 0.0
                page_text += block_text + "\n"
                confidence_sum += conf
                count += 1

                # Bounding box
                vertices = []
                if block.layout.bounding_poly and block.layout.bounding_poly.normalized_vertices:
                    vertices = [
                        {"x": v.x, "y": v.y}
                        for v in block.layout.bounding_poly.normalized_vertices
                    ]
                blocks.append({
                    "text": block_text,
                    "confidence": conf,
                    "vertices": vertices,
                })

            avg_conf = confidence_sum / count if count > 0 else 0.0
            pages.append(OCRPage(
                page_number=i + 1,
                text=page_text.strip(),
                confidence=avg_conf,
                blocks=blocks,
            ))

        full_text = document.text
        total_conf = sum(p.confidence for p in pages) / len(pages) if pages else 0.0

        logger.info(f"Document AI: {len(pages)} page(s), {len(full_text)} chars, conf={total_conf:.2f}")

        return OCRResult(
            pages=pages,
            full_text=full_text,
            average_confidence=total_conf,
            provider="google_docai",
            metadata={
                "detected_languages": [
                    lang.language_code
                    for page in document.pages
                    for lang in page.detected_languages
                ],
            },
        )

    @staticmethod
    def _get_text(layout, full_text: str) -> str:
        """Extrait le texte d'un layout a partir des text_segments."""
        text = ""
        if layout.text_anchor and layout.text_anchor.text_segments:
            for segment in layout.text_anchor.text_segments:
                start = int(segment.start_index) if segment.start_index else 0
                end = int(segment.end_index)
                text += full_text[start:end]
        return text.strip()
