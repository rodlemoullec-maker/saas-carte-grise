"""
Extracteur pour le Kbis / avis SIRENE (Document D-23).

L'extrait Kbis prouve l'existence légale de la société professionnelle.
"""
from __future__ import annotations

import re
from datetime import datetime
from typing import Any

from engine.extractors.base import BaseExtractor, ExtractionResult
from engine.models.documents import ExtractedKbis


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


class KbisExtractor(BaseExtractor[ExtractedKbis]):

    def extract_from_ocr_text(self, ocr_text: str) -> ExtractionResult:
        """Extraction par regex sur le texte OCR brut du Kbis / avis SIRENE."""
        text = ocr_text
        data: dict[str, Any] = {}

        # ── Détection du document ─────────────────────────────────────────────
        is_kbis = bool(re.search(
            r"[Kk]bis|extrait.*registre|[Rr]egistre\s*[Dd]u\s*[Cc]ommerce|RCS|SIRENE|[Aa]vis\s*[Ss]IRENE",
            text,
        ))

        # ── SIREN (9 chiffres) ────────────────────────────────────────────────
        m = re.search(r"(?:[Ss][Ii][Rr][Ee][Nn]\s*[:/]?\s*)(\d{3}\s?\d{3}\s?\d{3})", text)
        if not m:
            # Fallback : chercher 9 chiffres isolés (pas dans un SIRET plus long)
            m = re.search(r"\b(\d{3}\s?\d{3}\s?\d{3})(?!\s?\d)", text)
        if m:
            data["siren"] = re.sub(r"\s", "", m.group(1))

        # ── SIRET siège (14 chiffres) ─────────────────────────────────────────
        m = re.search(r"(?:[Ss][Ii][Rr][Ee][Tt]\s*[:/]?\s*)(\d{3}\s?\d{3}\s?\d{3}\s?\d{5})", text)
        if not m:
            m = re.search(r"\b(\d{3}\s?\d{3}\s?\d{3}\s?\d{5})\b", text)
        if m:
            siret = re.sub(r"\s", "", m.group(1))
            data["siret_siege"] = siret
            # Déduire SIREN si pas encore trouvé
            if not data.get("siren"):
                data["siren"] = siret[:9]

        # ── Raison sociale ────────────────────────────────────────────────────
        m = re.search(
            r"(?:[Dd]énomination|[Rr]aison\s*[Ss]ociale|[Nn]om\s*commercial)\s*[:/]?\s*"
            r"([A-ZÀÂÄÉÈÊËÎÏÔÙÛÜ][^\n]{2,60})",
            text,
        )
        if m:
            data["raison_sociale"] = m.group(1).strip().rstrip(".,;")

        # ── Représentant légal ────────────────────────────────────────────────
        m = re.search(
            r"(?:[Gg]érant|[Pp]résident|[Rr]eprésentant\s*légal|[Dd]irigeant|PDG|DG)\s*[:/]?\s*"
            r"([A-ZÀÂÄÉÈÊËÎÏÔÙÛÜ][A-Za-zÀ-ÿ]+(?:[ \t]+[A-Za-zÀ-ÿ]+)?)",
            text,
        )
        if m:
            parts = m.group(1).strip().split()
            if len(parts) >= 2:
                data["representant_nom"] = parts[0]
                data["representant_prenom"] = " ".join(parts[1:])
            elif parts:
                data["representant_nom"] = parts[0]

        # ── Adresse siège ─────────────────────────────────────────────────────
        m = re.search(
            r"(?:[Ss]iège\s*(?:social)?|[Aa]dresse)\s*[:/]?\s*([^\n]{5,80}(?:\n[^\n]{5,80})?)",
            text,
        )
        if m:
            adresse = " ".join(m.group(1).split("\n")).strip()
            data["adresse_siege"] = adresse[:120]

        # ── Date d'émission du Kbis ───────────────────────────────────────────
        m = re.search(
            r"(?:[Dd]élivré|[Ee]xtrait\s*au|[Dd]ate\s*[dD]'[eé]mission|[Ee]dité\s*le|[Dd]élivré\s*le)\s*[:/]?\s*"
            r"(\d{1,2}[./]\d{1,2}[./]\d{4})",
            text,
        )
        if not m:
            # Fallback: any date in the document
            m = re.search(r"\b(\d{1,2}[./]\d{1,2}[./]\d{4})\b", text)
        if m:
            data["date_kbis"] = _parse_date(m.group(1))

        # ── Validation ────────────────────────────────────────────────────────
        has_siren = bool(data.get("siren"))
        has_raison = bool(data.get("raison_sociale"))
        errors = []
        if not is_kbis:
            errors.append("Document non reconnu comme Kbis / avis SIRENE")
        if not has_siren:
            errors.append("SIREN introuvable")

        confidence = 0.0
        if is_kbis and has_siren and has_raison:
            confidence = 0.90
        elif is_kbis and has_siren:
            confidence = 0.75
        elif is_kbis or has_siren:
            confidence = 0.50
        else:
            confidence = 0.20

        return ExtractionResult(
            success=is_kbis and has_siren,
            data=data,
            errors=errors,
            confidence=confidence,
            raw_text=text[:500],
        )

    # ── Interface BaseExtractor ───────────────────────────────────────────────
    def get_extraction_prompt(self) -> str:
        return "Extrait les données du Kbis ou avis SIRENE de la société."

    def get_json_schema(self) -> dict[str, Any]:
        return ExtractedKbis.model_json_schema()

    def parse_response(self, raw_response: str) -> ExtractedKbis:
        return ExtractedKbis.model_validate_json(raw_response)

    def extract(self, ocr_text: str) -> ExtractionResult:
        return self.extract_from_ocr_text(ocr_text)
