"""
Extracteur pour l'attestation d'hébergement (ATTESTATION_HEBERGEMENT).

Document écrit à la main ou imprimé par lequel une personne (hébergeant)
certifie héberger une autre personne (hébergé) à son domicile.
Requis quand l'adresse du dossier ne correspond pas à un justificatif au nom du demandeur.
"""
from __future__ import annotations

import re
from datetime import datetime
from typing import Any

from engine.extractors.base import BaseExtractor, ExtractionResult
from engine.models.documents import ExtractedAttestationHebergement


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


class AttestationHebergementExtractor(BaseExtractor[ExtractedAttestationHebergement]):

    def extract_from_ocr_text(self, ocr_text: str) -> ExtractionResult:
        """Extraction par regex sur le texte OCR brut de l'attestation d'hébergement."""
        text = ocr_text
        data: dict[str, Any] = {}

        # ── Détection du document ─────────────────────────────────────────────
        is_attest = bool(re.search(
            r"[Aa]ttestation\s*d.[Hh]\u00e9bergement|"
            r"[Jj]e\s*soussign[e\u00e9][e]?.*h[e\u00e9]berg|"
            r"[Cc]ertifi[e\u00e9]?\s*h[e\u00e9]berger|"
            r"[Hh]\u00e9berge(?:ment|nt|r)\s|"
            r"[Dd]omicili[e\u00e9]\s*chez",
            text,
            re.IGNORECASE,
        ))

        # ── Hébergeant (soussigné) ────────────────────────────────────────────
        m = re.search(
            r"(?:[Jj]e\s*soussign[eé][e]?\s*[,:]?\s*|" 
            r"[Hh][eé]bergeant\s*[:/]?\s*|" 
            r"[Mm]on\s*nom\s*[:/]?\s*|" 
            r"[Nn]om\s*de\s*l['’]h[eé]bergeant\s*[:/]?\s*)"
            r"([A-ZÀÂÄÉÈÊËÎÏÔÙÛÜ]"
            r"[A-Za-zÀ-ÿ\- ]{2,40})",
            text,
        )
        if m:
            parts = m.group(1).strip().split()
            if parts:
                data["hebergeant_nom"] = parts[0]
                if len(parts) > 1:
                    data["hebergeant_prenom"] = " ".join(parts[1:])

        # ── Hébergé (personne hébergée) ───────────────────────────────────────
        m = re.search(
            r"(?:[Hh][eé]berg[eé][e]?\s*[:/]?\s*|"
            r"[Pp]ersonne\s*h[eé]berg[eé]e?\s*[:/]?\s*)"
            r"([A-ZÀÂÄÉÈÊËÎÏÔÙÛÜ]"
            r"[A-Za-zÀ-ÿ\- ]{2,40})",
            text,
        )
        if m:
            parts = m.group(1).strip().split()
            if parts:
                data["heberge_nom"] = parts[0]
                if len(parts) > 1:
                    data["heberge_prenom"] = " ".join(parts[1:])

        # ── Adresse d'hébergement ─────────────────────────────────────────────
        m = re.search(
            r"(?:[Aa]dresse\s*[:/]?\s*|[Dd]omicili[e\u00e9]\s*(?:au|à|a)\s*)"
            r"([^\n]{5,80})",
            text,
        )
        if m:
            data["adresse_hebergement"] = m.group(1).strip().rstrip(".,;")

        # ── Code postal + ville ───────────────────────────────────────────────
        m = re.search(r"\b(\d{5})\s+([A-Z\-]{2,30})\b", text)
        if m:
            data["code_postal"] = m.group(1)
            data["ville"] = m.group(2)

        # ── Date de l'attestation ─────────────────────────────────────────────
        m = re.search(
            r"(?:[Ff]ait\s*(?:le|à)|[Dd]ate\s*[:/]?|[Ss]ign[e\u00e9]\s*le)\s*"
            r"(\d{1,2}[./]\d{1,2}[./]\d{4})",
            text,
        )
        if not m:
            m = re.search(r"\b(\d{1,2}[./]\d{1,2}[./]\d{4})\b", text)
        if m:
            data["date_attestation"] = _parse_date(m.group(1))

        # ── Signature hébergeant ──────────────────────────────────────────────
        data["signature_hebergeant"] = bool(
            re.search(r"\[signature\]|\[SIGN[ÉE][E]?\]|[Ss]ignature", text)
            and not re.search(r"\[MISSING/BLANK\]|\[NON SIGN", text)
        )

        # ── Validation ────────────────────────────────────────────────────────
        has_hebergeant = bool(data.get("hebergeant_nom"))
        has_adresse = bool(data.get("adresse_hebergement") or data.get("code_postal"))
        errors = []
        if not is_attest:
            errors.append("Document non reconnu comme attestation d'hébergement")
        if not has_hebergeant:
            errors.append("Nom de l'hébergeant introuvable")
        if not has_adresse:
            errors.append("Adresse d'hébergement introuvable")

        if is_attest and has_hebergeant and has_adresse:
            confidence = 0.88
        elif is_attest and (has_hebergeant or has_adresse):
            confidence = 0.62
        elif is_attest:
            confidence = 0.40
        else:
            confidence = 0.20

        return ExtractionResult(
            success=is_attest and has_hebergeant,
            data=data,
            errors=errors,
            confidence=confidence,
            raw_text=text[:500],
        )

    # ── Interface BaseExtractor ───────────────────────────────────────────────
    def get_extraction_prompt(self) -> str:
        return "Extrait les données de l'attestation d'hébergement."

    def get_json_schema(self) -> dict[str, Any]:
        return ExtractedAttestationHebergement.model_json_schema()

    def parse_response(self, raw_response: str) -> ExtractedAttestationHebergement:
        return ExtractedAttestationHebergement.model_validate_json(raw_response)

    def extract(self, ocr_text: str) -> ExtractionResult:
        return self.extract_from_ocr_text(ocr_text)
