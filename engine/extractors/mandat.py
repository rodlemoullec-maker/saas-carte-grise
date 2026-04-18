"""
Extracteur pour le Mandat de vente / procuration (Cerfa 13757 — Document D-04).

Le mandant (propriétaire du véhicule) autorise le professionnel (mandataire)
à effectuer les démarches de cession en son nom.
"""
from __future__ import annotations

import re
from datetime import datetime
from typing import Any

from engine.extractors.base import BaseExtractor, ExtractionResult
from engine.models.documents import ExtractedMandat
from engine.ocr_patterns import OptimizedExtraction


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


class MandatExtractor(BaseExtractor[ExtractedMandat]):

    def extract_from_ocr_text(self, ocr_text: str) -> ExtractionResult:
        """Extraction par regex sur le texte OCR brut du mandat Cerfa 13757."""
        text = ocr_text
        data: dict[str, Any] = {}

        # ── Détection du document ─────────────────────────────────────────────
        is_mandat = bool(re.search(
            r"[Mm]andat|[Pp]rocuration|[Cc]erfa.*13757|13757.*[Cc]erfa|"
            r"[Mm]andant|[Mm]andataire|[Pp]ouvoir\s*(?:de\s*vente|spécial)",
            text,
            re.IGNORECASE,
        ))

        # ── VIN ───────────────────────────────────────────────────────────────
        m = VIN_RE.search(text)
        if m:
            data["vin"] = m.group(1)

        # ── VIN — Pattern optimisé robuste aux variations OCR ─────────────────
        vin = OptimizedExtraction.extract_vin(text)
        if vin:
            data["vin"] = vin

        # ── Immatriculation ────────────────────────────────────────
        m = IMMAT_RE.search(text)
        if m:
            data["immatriculation"] = m.group(1).replace(" ", "-").upper()

        # ── Mandant (propriétaire-vendeur) ────────────────────────────────────
        # "Mandant : DUPONT Jean" ou "Je soussigné MARTIN Sophie, propriétaire"
        m = re.search(
            r"[Mm]andant\s*[:/]?\s*"
            r"(?:[Mm]r\.?\s*|[Mm]me\.?\s*|[Mm]/\s*)?"
            r"([A-ZÀÂÄÉÈÊËÎÏÔÙÛÜ][A-Za-zÀ-ÿ\- ]{2,40})",
            text,
        )
        if not m:
            # "Je soussigné MARTIN Sophie" ou "soussigné(e) DUPONT Jean"
            m = re.search(
                r"[Ss]oussigné[e]?[,\s]+"
                r"([A-ZÀÂÄÉÈÊËÎÏÔÙÛÜ][A-Za-zÀ-ÿ\- ]{2,40}?)(?:[,\n]|propriétaire|vendeur)",
                text,
            )
        if m:
            parts = m.group(1).strip().split()
            data["mandant_nom"] = parts[0]
            if len(parts) > 1:
                data["mandant_prenom"] = " ".join(parts[1:])

        # ── Mandataire (professionnel) ────────────────────────────────────────
        m = re.search(
            r"(?:[Mm]andataire|[Aa]utori[sz]e\s*(?:M\.|Mme\.?\s*)?|[Pp]rofessionnel)\s*[:/]?\s*"
            r"([A-ZÀÂÄÉÈÊËÎÏÔÙÛÜ][^\n]{2,60})",
            text,
        )
        if m:
            data["mandataire_nom"] = m.group(1).strip().rstrip(".,;")

        # ── SIRET du mandataire ───────────────────────────────────────────────
        m_siret = SIRET_RE.search(text)
        if m_siret:
            data["mandataire_siret"] = re.sub(r"\s", "", m_siret.group(1))

        # ── Date du mandat ────────────────────────────────────────────────────
        m = re.search(
            r"(?:[Ff]ait\s*le|[Dd]ate\s*[:/]?|[Ss]igné\s*le)\s*"
            r"(\d{1,2}[./]\d{1,2}[./]\d{4})",
            text,
        )
        if not m:
            m = re.search(r"\b(\d{1,2}[./]\d{1,2}[./]\d{4})\b", text)
        if m:
            data["date_mandat"] = _parse_date(m.group(1))

        # ── Signature du mandant — Détection robuste trois états ─────────────
        sig = OptimizedExtraction.is_signature_present(text)
        data["signature_mandant"] = bool(sig)  # None (indéterminé) → False par sécurité

        # ── Validation ────────────────────────────────────────────────────────
        has_vin = bool(data.get("vin"))
        has_immat = bool(data.get("immatriculation"))
        has_mandant = bool(data.get("mandant_nom"))
        errors = []
        if not is_mandat:
            errors.append("Document non reconnu comme mandat (Cerfa 13757)")
        if not has_vin and not has_immat:
            errors.append("VIN et immatriculation manquants")
        if not has_mandant:
            errors.append("Mandant introuvable")

        if is_mandat and has_mandant and (has_vin or has_immat):
            confidence = 0.88
        elif is_mandat and (has_mandant or has_vin or has_immat):
            confidence = 0.62
        elif is_mandat:
            confidence = 0.42
        else:
            confidence = 0.20

        return ExtractionResult(
            success=is_mandat and (has_vin or has_immat),
            data=data,
            errors=errors,
            confidence=confidence,
            raw_text=text[:500],
        )

    # ── Interface BaseExtractor ───────────────────────────────────────────────
    def get_extraction_prompt(self) -> str:
        return "Extrait les données du mandat de vente (Cerfa 13757)."

    def get_json_schema(self) -> dict[str, Any]:
        return ExtractedMandat.model_json_schema()

    def parse_response(self, raw_response: str) -> ExtractedMandat:
        return ExtractedMandat.model_validate_json(raw_response)

    def extract(self, ocr_text: str) -> ExtractionResult:
        return self.extract_from_ocr_text(ocr_text)
