"""
Extracteur pour la CNI de l'hébergeant (CNI_HEBERGEANT).

Document identique à une CNI classique, mais appartenant à la personne
qui héberge le demandeur. La logique d'extraction est la même que pour
IdentiteExtractor, mais le type de document est distinct pour le dossier.
"""
from __future__ import annotations

import re
from datetime import datetime
from typing import Any

from engine.extractors.base import BaseExtractor, ExtractionResult
from engine.models.documents import ExtractedCNIHebergeant
from engine.ocr_patterns import OptimizedExtraction


def _parse_date(s: str) -> str | None:
    for fmt in ("%d.%m.%Y", "%d/%m/%Y", "%d-%m-%Y", "%d.%m.%y", "%d/%m/%y",
                "%Y-%m-%d", "%d %b %Y"):
        try:
            d = datetime.strptime(s.strip(), fmt)
            if d.year > 2050:
                d = d.replace(year=d.year - 100)
            return d.strftime("%Y-%m-%d")
        except ValueError:
            continue
    return None


class CNIHebergeantExtractor(BaseExtractor[ExtractedCNIHebergeant]):

    def extract_from_ocr_text(self, ocr_text: str) -> ExtractionResult:
        """Extraction par regex sur le texte OCR brut de la CNI de l'hébergeant."""
        text = ocr_text
        data: dict[str, Any] = {}

        # ── Détection du document (CNI ou passeport français) ─────────────────
        is_cni = bool(re.search(
            r"[Cc]arte\s*[Nn]ationale\s*d.[Ii]dentit[eé]|CNI|"
            r"[Pp]ASSEPORT|PASSPORT|"
            r"CARTE\s*D.IDENTIT|REPUBLIQUE\s*FRANÇAISE|"
            r"IDENTITY\s*CARD|CARTE\s*NATIONALE",
            text,
            re.IGNORECASE,
        ))

        # ── Nom ───────────────────────────────────────────────────────────────
        m = re.search(
            r"(?:[Nn]om\s*[:/]?\s*|NOM\s*(?:/\s*NAME)?\s*[:/]\s*)([A-ZÀÂÄÉÈÊËÎÏÔÙÛÜ][A-ZÀÂÄÉÈÊËÎÏÔÙÛÜ\- ]{1,35})",
            text,
        )
        if m:
            # Reject if captured value looks like a field label
            val = m.group(1).strip()
            if val not in ("NAME", "PRÉNOM", "PRENOM", "NOM"):
                data["nom"] = val

        # ── Prénom ────────────────────────────────────────────────────────────
        m = re.search(
            r"(?:[Pp]r[eé]noms?\s*[:/]?\s*|PRÉNOM\s*:?\s*)([A-ZÀÂÄÉÈÊËÎÏÔÙÛÜ][A-Za-zÀ-ÿ\- ]{1,40})",
            text,
        )
        if m:
            data["prenom"] = m.group(1).strip()

        # ── Date de naissance ─────────────────────────────────────────────────
        m = re.search(
            r"(?:[Nn][eé][e]?\s*(?:le)?\s*[:/]?|[Dd]ate\s*de\s*naissance\s*[:/]?|"
            r"N[eé]\s*le\s*:?)\s*(\d{1,2}[./]\d{1,2}[./]\d{4})",
            text,
        )
        if m:
            data["date_naissance"] = _parse_date(m.group(1))

        # ── Lieu de naissance ─────────────────────────────────────────────────
        m = re.search(
            r"(?:[Ll]ieu\s*(?:de\s*)?naissance|[Nn][eé][e]?\s*(?:le\s*[\d./]+\s*)?[\u00e0a]\s*)\s*[:/]?\s*"
            r"([A-ZÀÂÄÉÈÊËÎÏÔÙÛÜ][A-Za-zÀ-ÿ\- ]{2,40})",
            text,
        )
        if m:
            data["lieu_naissance"] = m.group(1).strip()

        # ── Numéro de document ────────────────────────────────────────────────
        # CNI : 12 chiffres  |  Passeport : 2 lettres + 7 chiffres
        m = re.search(r"\b(\d{12})\b", text)
        if not m:
            m = re.search(r"\b([A-Z]{2}\d{7})\b", text)
        if m:
            data["numero_document"] = m.group(1)

        # ── Date d'expiration ─────────────────────────────────────────────────
        m = re.search(
            r"(?:[Ee]xpir[ae]|[Vv]alable\s*jusqu['’]?au?|[Dd]ate\s*d.[eé]ch[eé]ance|"
            r"[Ff]in\s*de\s*validit[eé])\s*[:/]?\s*(\d{1,2}[./]\d{1,2}[./]\d{4})",
            text,
        )
        if m:
            data["date_expiration"] = _parse_date(m.group(1))

        # ── Nationalité ───────────────────────────────────────────────────────
        m = re.search(
            r"(?:[Nn]ationalit[eé]|NATIONALITÉ)\s*[:/]?\s*([A-ZÀÂÄÉÈÊËÎÏÔÙÛÜ][A-Za-zÀ-ÿ]{3,20})",
            text,
        )
        if m:
            data["nationalite"] = m.group(1).strip()
        elif is_cni:
            # Par défaut pour un document français
            data["nationalite"] = "FRANÇAISE"

        # ── Validation ────────────────────────────────────────────────────────
        has_nom = bool(data.get("nom"))
        has_num = bool(data.get("numero_document"))
        errors = []
        if not is_cni:
            errors.append("Document non reconnu comme CNI ou passeport")
        if not has_nom:
            errors.append("Nom introuvable")

        if is_cni and has_nom and has_num:
            confidence = 0.90
        elif is_cni and has_nom:
            confidence = 0.72
        elif is_cni:
            confidence = 0.45
        else:
            confidence = 0.20

        return ExtractionResult(
            success=is_cni and has_nom,
            data=data,
            errors=errors,
            confidence=confidence,
            raw_text=text[:500],
        )

    # ── Interface BaseExtractor ───────────────────────────────────────────────
    def get_extraction_prompt(self) -> str:
        return "Extrait les données de la CNI de l'hébergeant."

    def get_json_schema(self) -> dict[str, Any]:
        return ExtractedCNIHebergeant.model_json_schema()

    def parse_response(self, raw_response: str) -> ExtractedCNIHebergeant:
        return ExtractedCNIHebergeant.model_validate_json(raw_response)

    def extract(self, ocr_text: str) -> ExtractionResult:
        return self.extract_from_ocr_text(ocr_text)
