"""
Extracteur pour le Certificat de cession tamponné pro (CERTIFICAT_CESSION).

Même document que la cession (Cerfa 15776) mais dans l'état où il a été
déposé par le professionnel : avec le cachet pro apposé et potentiellement
une copie de la préfecture. Différence métier avec ExtractedCession :
- tampon_pro doit être True
- numéro cerfa "15776" vérifié
"""
from __future__ import annotations

import re
from datetime import datetime
from typing import Any

from engine.extractors.base import BaseExtractor, ExtractionResult
from engine.models.documents import ExtractedCertificatCession


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


class CertificatCessionExtractor(BaseExtractor[ExtractedCertificatCession]):

    def extract_from_ocr_text(self, ocr_text: str) -> ExtractionResult:
        """Extraction par regex sur le texte OCR brut du certificat de cession tamponné."""
        text = ocr_text
        data: dict[str, Any] = {}

        # ── Détection du document ─────────────────────────────────────────────
        is_cession = bool(re.search(
            r"[Cc]ertificat\s*de\s*[Cc]ession|[Cc]ession\s*de\s*[Vv][eé]hicule|"
            r"15776|[Cc]erfa.*15\s*776|[Dd]éclaration\s*de\s*[Cc]ession",
            text,
        ))

        # ── Numéro Cerfa ──────────────────────────────────────────────────────
        m = re.search(r"15\s*776", text)
        if m:
            data["numero_cerfa"] = "15776"

        # ── VIN ───────────────────────────────────────────────────────────────
        m = VIN_RE.search(text)
        if m:
            data["vin"] = m.group(1)

        # ── Immatriculation ───────────────────────────────────────────────────
        m = IMMAT_RE.search(text)
        if m:
            data["immatriculation"] = m.group(1).replace(" ", "-").upper()

        # ── Vendeur ───────────────────────────────────────────────────────────
        m = re.search(
            r"(?:[Vv]endeur|[Cc][eé]dant|[Aa]ncien\s*propri[eé]taire)\s*[:/]?\s*"
            r"([A-ZÀÂÄÉÈÊËÎÏÔÙÛÜ][A-Za-zÀ-ÿ\- ]{2,40})",
            text,
        )
        if m:
            data["vendeur_nom"] = m.group(1).strip()

        # ── SIRET vendeur ─────────────────────────────────────────────────────
        m_siret = SIRET_RE.search(text)
        if m_siret:
            data["vendeur_siret"] = re.sub(r"\s", "", m_siret.group(1))

        # ── Acheteur ──────────────────────────────────────────────────────────
        m = re.search(
            r"(?:[Aa]cqu[eé]reur|[Aa]cheteur|[Nn]ouveau\s*propri[eé]taire)\s*[:/]?\s*"
            r"([A-ZÀÂÄÉÈÊËÎÏÔÙÛÜ][A-Za-zÀ-ÿ\- ]{2,40})",
            text,
        )
        if m:
            data["acheteur_nom"] = m.group(1).strip()

        # ── Date de cession ───────────────────────────────────────────────────
        m = re.search(
            r"(?:[Dd]ate\s*de\s*[Cc]ession|[Vv]endu\s*le|[Cc][eé]d[eé]\s*le)\s*[:/]?\s*"
            r"(\d{1,2}[./]\d{1,2}[./]\d{4})",
            text,
        )
        if not m:
            m = re.search(r"\b(\d{1,2}[./]\d{1,2}[./]\d{4})\b", text)
        if m:
            data["date_cession"] = _parse_date(m.group(1))

        # ── Signatures ────────────────────────────────────────────────────────
        has_sig = bool(re.search(r"\[signature\]|\[SIGN[ÉE][E]?\]", text)
                       and not re.search(r"\[MISSING/BLANK\]", text))
        data["signatures_vendeur"] = has_sig
        data["signature_acheteur"] = bool(
            re.search(r"[Ss]ignature.*[Aa]cqu[eé]reur|[Aa]cqu[eé]reur.*[Ss]ignature", text)
            and has_sig
        )

        # ── Tampon professionnel ──────────────────────────────────────────────
        # Le tampon pro est le différenciateur clé de ce document vs CERFA_CESSION
        data["tampon_pro"] = bool(
            re.search(r"\[tampon\]|\[cachet\]|\[TAMPON\]|\[CACHET\]|[Cc]achet\s*[Pp]ro|"
                      r"SIRET\s*:\s*\d", text)
        )

        # ── Validation ────────────────────────────────────────────────────────
        has_vin = bool(data.get("vin"))
        has_immat = bool(data.get("immatriculation"))
        errors = []
        if not is_cession:
            errors.append("Document non reconnu comme certificat de cession (Cerfa 15776)")
        if not has_vin and not has_immat:
            errors.append("VIN et immatriculation manquants")
        if not data.get("tampon_pro"):
            errors.append("Cachet/tampon professionnel absent")

        if is_cession and (has_vin or has_immat) and data.get("tampon_pro"):
            confidence = 0.90
        elif is_cession and (has_vin or has_immat):
            confidence = 0.68
        elif is_cession:
            confidence = 0.45
        else:
            confidence = 0.20

        return ExtractionResult(
            success=is_cession and (has_vin or has_immat),
            data=data,
            errors=errors,
            confidence=confidence,
            raw_text=text[:500],
        )

    # ── Interface BaseExtractor ───────────────────────────────────────────────
    def get_extraction_prompt(self) -> str:
        return "Extrait les données du certificat de cession tamponné (Cerfa 15776)."

    def get_json_schema(self) -> dict[str, Any]:
        return ExtractedCertificatCession.model_json_schema()

    def parse_response(self, raw_response: str) -> ExtractedCertificatCession:
        return ExtractedCertificatCession.model_validate_json(raw_response)

    def extract(self, ocr_text: str) -> ExtractionResult:
        return self.extract_from_ocr_text(ocr_text)
