"""
Extracteur pour l'Attestation de suivi de formation 7h moto (ATTESTATION_FORMATION).

Obligatoire pour les conducteurs de 125cc (A1/A2) ou L5e qui souhaitent
conduire avec le permis B + 7 heures de formation.
"""
from __future__ import annotations

import re
from datetime import datetime
from typing import Any

from engine.extractors.base import BaseExtractor, ExtractionResult
from engine.models.documents import ExtractedAttestationFormation
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


class AttestationFormationExtractor(BaseExtractor[ExtractedAttestationFormation]):

    def extract_from_ocr_text(self, ocr_text: str) -> ExtractionResult:
        """Extraction par regex sur le texte OCR brut de l'attestation de formation."""
        text = ocr_text
        data: dict[str, Any] = {}

        # ── Détection du document ─────────────────────────────────────────────
        is_attest = bool(re.search(
            r"[Aa]ttestation\s*(?:de\s*)?[Ff]ormation|"
            r"[Ff]ormation\s*(?:7\s*h|sept\s*heures|moto)|"
            r"[Pp]ermis\s*[Bb]\s*\+\s*(?:7|sept)|"
            r"125\s*cm[³3]|[Ll]5[Ee]|"
            r"conduite?\s*accompagnée|AA\s*moto",
            text,
            re.IGNORECASE,
        ))

        # ── Nom et prénom du stagiaire ────────────────────────────────────────
        m = re.search(
            r"(?:[Ss]tagiaire|[Ee]lève|[Cc]andidats?|[Nn]om\s*[:/]?|[Pp]rénom\s*[:/]?)\s*[:/]?\s*"
            r"(?:[Mm][Rr]?\.?\s*|[Mm][Mm][Ee]\.?\s*)?"
            r"([A-ZÀÂÄÉÈÊËÎÏÔÙÛÜ][A-Za-zÀ-ÿ\- ]{2,40})",
            text,
        )
        if m:
            parts = m.group(1).strip().split()
            if parts:
                data["nom_stagiaire"] = parts[0]
                if len(parts) > 1:
                    data["prenom_stagiaire"] = " ".join(parts[1:])

        # ── Date de naissance ─────────────────────────────────────────────────
        m = re.search(
            r"(?:[Nn]é[e]?\s*(?:le)?|[Dd]ate\s*de\s*[Nn]aissance)\s*[:/]?\s*"
            r"(\d{1,2}[./]\d{1,2}[./]\d{4})",
            text,
        )
        if m:
            data["date_naissance"] = _parse_date(m.group(1))

        # ── Organisme de formation ────────────────────────────────────────────
        m = re.search(
            r"(?:[Oo]rganisme|[Ee]cole\s*de\s*conduite|[Aa]uto[\-\s]?[Ee]cole|"
            r"[Cc]entre\s*de\s*[Ff]ormation)\s*[:/]?\s*([^\n]{3,60})",
            text,
        )
        if m:
            data["organisme_formation"] = m.group(1).strip().rstrip(".,;")

        # ── Date de la formation ──────────────────────────────────────────────
        m = re.search(
            r"(?:[Ff]ormation\s*(?:réalisée|effectuée|dispensée)\s*(?:le)?|"
            r"[Dd]ate\s*(?:de\s*)?[Ff]ormation)\s*[:/]?\s*"
            r"(\d{1,2}[./]\d{1,2}[./]\d{4})",
            text,
        )
        if not m:
            # Dernier recours : première date dans le document
            m = re.search(r"\b(\d{1,2}[./]\d{1,2}[./]\d{4})\b", text)
        if m:
            data["date_formation"] = _parse_date(m.group(1))

        # ── Durée en heures ───────────────────────────────────────────────────
        m = re.search(r"(\d+)\s*[Hh](?:eures?)?(?:\s*de\s*formation)?", text)
        if m:
            data["duree_heures"] = int(m.group(1))

        # ── Type de formation ─────────────────────────────────────────────────
        if re.search(r"[Ll]5[Ee]|triporteur|quadricycle\s*lourd", text, re.IGNORECASE):
            data["type_formation"] = "L5e"
        elif re.search(r"125\s*cm[³3]|125\s*cc|A1|A2|moto", text, re.IGNORECASE):
            data["type_formation"] = "125cc"
        else:
            data["type_formation"] = "moto"

        # ── Numéro d'attestation ──────────────────────────────────────────────
        m = re.search(
            r"(?:[Nn][°º]?\s*[Aa]ttestation|[Rr]éférence)\s*[:/]?\s*([A-Z0-9\-\/]{4,25})",
            text,
        )
        if m:
            data["numero_attestation"] = m.group(1).strip()

        # ── Signature de l'organisme ──────────────────────────────────────────
        data["signature_organisme"] = bool(
            re.search(r"\[signature\]|\[SIGN[ÉE][E]?\]|[Cc]achet\s*(?:et\s*)?[Ss]ignature", text)
            and not re.search(r"\[MISSING/BLANK\]|\[NON SIGNÉE\]", text)
        )

        # ── Validation ────────────────────────────────────────────────────────
        has_nom = bool(data.get("nom_stagiaire"))
        has_date = bool(data.get("date_formation"))
        duree = data.get("duree_heures", 0) or 0
        errors = []
        if not is_attest:
            errors.append("Document non reconnu comme attestation de formation moto")
        if not has_nom:
            errors.append("Nom du stagiaire introuvable")
        if duree and duree < 7:
            errors.append(f"Durée insuffisante : {duree}h (minimum 7h requis)")

        if is_attest and has_nom and has_date and duree >= 7:
            confidence = 0.90
        elif is_attest and (has_nom or has_date):
            confidence = 0.65
        elif is_attest:
            confidence = 0.42
        else:
            confidence = 0.20

        return ExtractionResult(
            success=is_attest and has_nom,
            data=data,
            errors=errors,
            confidence=confidence,
            raw_text=text[:500],
        )

    # ── Interface BaseExtractor ───────────────────────────────────────────────
    def get_extraction_prompt(self) -> str:
        return "Extrait les données de l'attestation de formation moto 7h."

    def get_json_schema(self) -> dict[str, Any]:
        return ExtractedAttestationFormation.model_json_schema()

    def parse_response(self, raw_response: str) -> ExtractedAttestationFormation:
        return ExtractedAttestationFormation.model_validate_json(raw_response)

    def extract(self, ocr_text: str) -> ExtractionResult:
        return self.extract_from_ocr_text(ocr_text)
