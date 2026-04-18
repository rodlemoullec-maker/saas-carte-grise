"""
Extracteur pour le Récépissé de Déclaration d'Achat (Document D-21).

La préfecture remet ce récépissé au professionnel après enregistrement de
la DA. Il permet de circuler légalement pendant le délai de 30 jours
avant cession finale.
"""
from __future__ import annotations

import re
from datetime import datetime
from typing import Any

from engine.extractors.base import BaseExtractor, ExtractionResult
from engine.models.documents import ExtractedRecepisseDA


def _parse_date(s: str) -> str | None:
    for fmt in ("%d.%m.%Y", "%d/%m/%Y", "%d-%m-%Y", "%d.%m.%y", "%d/%m/%y"):
        try:
            d = datetime.strptime(s.strip(), fmt)
            if d.year > 2050:
                d = d.replace(year=d.year - 100)
            return d.strftime("%Y-%m-%d")
        except ValueError:
            continue
    return None


VIN_RE = re.compile(r"(?<![A-HJ-NPR-Z0-9])([A-HJ-NPR-Z0-9]{17,18})(?![A-HJ-NPR-Z0-9])")
IMMAT_RE = re.compile(r"\b([A-Z]{2}[\-\s]?\d{3}[\-\s]?[A-Z]{2})\b")


class RecepissedaExtractor(BaseExtractor[ExtractedRecepisseDA]):

    def extract_from_ocr_text(self, ocr_text: str) -> ExtractionResult:
        """Extraction par regex sur le texte OCR brut du récépissé de DA."""
        text = ocr_text
        data: dict[str, Any] = {}

        # ── Détection du document ─────────────────────────────────────────────
        is_recepisseDA = bool(re.search(
            r"[Rr]écépissé|[Rr]ecepisse|[Rr][Éé][Cc][Éé][Pp][Ii][Ss][Ss][Éé]|"
            r"[Dd]éclaration\s*d.[Aa]chat|[Dd][Éé][Cc][Ll][Aa][Rr][Aa][Tt][Ii][Oo][Nn].*[Aa][Cc][Hh][Aa][Tt]",
            text,
        ))

        # ── VIN ───────────────────────────────────────────────────────────────
        m = VIN_RE.search(text)
        if m:
            data["vin"] = m.group(1)

        # ── Immatriculation ───────────────────────────────────────────────────
        m = IMMAT_RE.search(text)
        if m:
            data["immatriculation"] = m.group(1).replace(" ", "-").upper()

        # ── SIREN / SIRET du professionnel ────────────────────────────────────
        m = re.search(r"\b(\d{3}\s?\d{3}\s?\d{3}\s?\d{5})\b", text)
        if m:
            siret = re.sub(r"\s", "", m.group(1))
            data["siren_pro"] = siret[:9]
        else:
            m = re.search(r"\b(\d{3}\s?\d{3}\s?\d{3})(?!\s?\d)", text)
            if m:
                data["siren_pro"] = re.sub(r"\s", "", m.group(1))

        # ── Date d'enregistrement ─────────────────────────────────────────────
        m = re.search(
            r"(?:[Ee]nregistré|[Rr]eçu|[Dd]ate)\s*(?:le|:)?\s*"
            r"(\d{1,2}[./]\d{1,2}[./]\d{4})",
            text,
        )
        if not m:
            # Cherche toute date présente
            m = re.search(r"\b(\d{1,2}[./]\d{1,2}[./]\d{4})\b", text)
        if m:
            data["date_enregistrement"] = _parse_date(m.group(1))

        # ── Validation ────────────────────────────────────────────────────────
        has_vin = bool(data.get("vin"))
        has_immat = bool(data.get("immatriculation"))
        has_siren = bool(data.get("siren_pro"))
        has_date = bool(data.get("date_enregistrement"))
        errors = []
        if not is_recepisseDA:
            errors.append("Document non reconnu comme récépissé de DA")
        if not has_vin and not has_immat:
            errors.append("VIN et immatriculation manquants")
        if not has_date:
            errors.append("Date d'enregistrement introuvable")

        if is_recepisseDA and (has_vin or has_immat) and has_date:
            confidence = 0.88
        elif is_recepisseDA and (has_vin or has_immat or has_date):
            confidence = 0.60
        elif is_recepisseDA:
            confidence = 0.40
        else:
            confidence = 0.20

        return ExtractionResult(
            success=is_recepisseDA and (has_vin or has_immat),
            data=data,
            errors=errors,
            confidence=confidence,
            raw_text=text[:500],
        )

    # ── Interface BaseExtractor ───────────────────────────────────────────────
    def get_extraction_prompt(self) -> str:
        return "Extrait les données du récépissé de déclaration d'achat."

    def get_json_schema(self) -> dict[str, Any]:
        return ExtractedRecepisseDA.model_json_schema()

    def parse_response(self, raw_response: str) -> ExtractedRecepisseDA:
        return ExtractedRecepisseDA.model_validate_json(raw_response)

    def extract(self, ocr_text: str) -> ExtractionResult:
        return self.extract_from_ocr_text(ocr_text)
