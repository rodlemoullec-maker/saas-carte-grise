"""
Extracteur pour la Déclaration d'Achat pro (Cerfa 13751 — Document D-05).

La DA est déposée par le professionnel à la préfecture dans les 15 jours
suivant l'achat du véhicule d'occasion. Elle suspend l'obligation de
demander un nouveau certificat d'immatriculation.
"""
from __future__ import annotations

import re
from datetime import datetime
from typing import Any

from engine.extractors.base import BaseExtractor, ExtractionResult
from engine.models.documents import ExtractedDA


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
SIRET_RE = re.compile(r"\b(\d{3}\s?\d{3}\s?\d{3}\s?\d{5})\b")
SIREN_RE = re.compile(r"\b(\d{3}\s?\d{3}\s?\d{3})(?!\s?\d)")


class DAExtractor(BaseExtractor[ExtractedDA]):

    def extract_from_ocr_text(self, ocr_text: str) -> ExtractionResult:
        """Extraction par regex sur le texte OCR brut de la déclaration d'achat."""
        text = ocr_text
        data: dict[str, Any] = {}

        # ── Détection du document ─────────────────────────────────────────────
        is_da = bool(re.search(
            r"[Dd]éclaration\s*d.[Aa]chat|[Cc]erfa.*13751|13751.*[Cc]erfa|"
            r"D\.A\.|[Dd]écl[aâ]\.\s*[Aa]chat",
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

        # ── SIRET du professionnel ────────────────────────────────────────────
        m = re.search(
            r"(?:[Ss][Ii][Rr][Ee][Tt]|[Nn]°\s*[Ss]IRET)\s*[:/]?\s*"
            r"(\d{3}\s?\d{3}\s?\d{3}\s?\d{5})",
            text,
        )
        if not m:
            m = SIRET_RE.search(text)
        if m:
            siret = re.sub(r"\s", "", m.group(1))
            data["siret_pro"] = siret
            data["siren_pro"] = siret[:9]

        # ── SIREN seul si pas de SIRET ────────────────────────────────────────
        if not data.get("siren_pro"):
            m = re.search(
                r"(?:[Ss][Ii][Rr][Ee][Nn])\s*[:/]?\s*(\d{3}\s?\d{3}\s?\d{3})(?!\s?\d)",
                text,
            )
            if m:
                data["siren_pro"] = re.sub(r"\s", "", m.group(1))

        # ── Nom du professionnel ──────────────────────────────────────────────
        m = re.search(
            r"(?:[Nn]om\s*(?:du\s*)?[Pp]ro(?:fessionnel)?|[Rr]aison\s*[Ss]ociale|[Aa]cquéreur)\s*[:/]?\s*"
            r"([A-ZÀÂÄÉÈÊËÎÏÔÙÛÜ][^\n]{2,60})",
            text,
        )
        if m:
            data["nom_pro"] = m.group(1).strip().rstrip(".,;")

        # ── Date d'achat ──────────────────────────────────────────────────────
        m = re.search(
            r"(?:[Dd]ate\s*(?:d.[Aa]chat|d'[Aa]cquisition)|[Aa]cheté\s*le)\s*[:/]?\s*"
            r"(\d{1,2}[./]\d{1,2}[./]\d{4})",
            text,
        )
        if m:
            data["date_achat"] = _parse_date(m.group(1))

        # ── Nom du vendeur (titulaire de la CG cédée) ─────────────────────────
        m = re.search(
            r"(?:[Vv]endeur|[Cc]édant|[Tt]itulaire.*[Cc][Gg])\s*[:/]?\s*"
            r"([A-ZÀÂÄÉÈÊËÎÏÔÙÛÜ][A-Za-zÀ-ÿ\- ]{2,40})",
            text,
        )
        if m:
            data["vendeur_nom"] = m.group(1).strip()

        # ── Validation ────────────────────────────────────────────────────────
        has_vin = bool(data.get("vin"))
        has_immat = bool(data.get("immatriculation"))
        has_siren = bool(data.get("siren_pro"))
        errors = []
        if not is_da:
            errors.append("Document non reconnu comme déclaration d'achat (Cerfa 13751)")
        if not has_vin and not has_immat:
            errors.append("VIN et immatriculation manquants")
        if not has_siren:
            errors.append("SIREN/SIRET professionnel introuvable")

        if is_da and has_siren and (has_vin or has_immat):
            confidence = 0.90
        elif is_da and (has_siren or has_vin or has_immat):
            confidence = 0.65
        elif is_da:
            confidence = 0.45
        else:
            confidence = 0.20

        return ExtractionResult(
            success=is_da and (has_vin or has_immat) and has_siren,
            data=data,
            errors=errors,
            confidence=confidence,
            raw_text=text[:500],
        )

    # ── Interface BaseExtractor ───────────────────────────────────────────────
    def get_extraction_prompt(self) -> str:
        return "Extrait les données de la déclaration d'achat (Cerfa 13751)."

    def get_json_schema(self) -> dict[str, Any]:
        return ExtractedDA.model_json_schema()

    def parse_response(self, raw_response: str) -> ExtractedDA:
        return ExtractedDA.model_validate_json(raw_response)

    def extract(self, ocr_text: str) -> ExtractionResult:
        return self.extract_from_ocr_text(ocr_text)
