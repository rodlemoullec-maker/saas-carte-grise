"""
Extracteur pour le certificat de cession (Cerfa 15776).

Document déposé par le vendeur pro (déjà signé lors de la vente).
Le système vérifie :
- Nom vendeur / nom acquéreur
- Date de cession (doit correspondre à la date de vente sur la CG barrée)
- VIN / immatriculation
- Présence des signatures
"""
from __future__ import annotations

import re
from datetime import datetime
from typing import Any

from engine.extractors.base import BaseExtractor, ExtractionResult
from engine.models.documents import ExtractedCession


def _parse_date(date_str: str) -> str | None:
    if not date_str:
        return None
    for fmt in ("%d.%m.%Y", "%d/%m/%Y", "%d.%m.%y", "%d/%m/%y"):
        try:
            d = datetime.strptime(date_str.strip(), fmt)
            if d.year > 2050:
                d = d.replace(year=d.year - 100)
            return d.strftime("%Y-%m-%d")
        except ValueError:
            continue
    return None


class CessionExtractor(BaseExtractor[ExtractedCession]):

    def extract_from_ocr_text(self, ocr_text: str) -> ExtractionResult:
        """Extraction par regex sur le texte OCR brut du certificat de cession."""
        text = ocr_text
        data: dict[str, Any] = {}

        # Ancien propriétaire (vendeur)
        m = re.search(
            r"[Aa]ncien\s*propri[eé]taire\s*[:\s]*\n?\s*([A-Z][A-Za-zÀ-ÿ\- ]{2,50})",
            text
        )
        if m:
            data["vendeur_nom"] = m.group(1).strip()

        # Nouveau propriétaire (acquéreur)
        m = re.search(
            r"[Nn]ouveau\s*propri[eé]taire\s*[:\s]*\n?\s*([A-Z][A-Za-zÀ-ÿ\- ]{2,50})",
            text
        )
        if m:
            data["acheteur_nom"] = m.group(1).strip()

        # Date de cession
        m = re.search(
            r"[Dd]ate\s*(?:et\s*heure)?\s*(?:de\s*(?:la\s*)?)?cession\s*[:\s]*(\d{2}[./]\d{2}[./]\d{2,4})",
            text
        )
        if m:
            data["date_cession"] = m.group(1)
        if not data.get("date_cession"):
            m = re.search(r"[Cc][eé]d[eé]\s*le\s*[:\s]*(\d{2}[./]\d{2}[./]\d{2,4})", text)
            if m:
                data["date_cession"] = m.group(1)

        # Immatriculation
        m = re.search(
            r"[Ii]mmatriculation\s*[:\s]*([A-Z]{2}[\-\s]?\d{3}[\-\s]?[A-Z]{2})",
            text
        )
        if m:
            data["immatriculation"] = m.group(1).strip()

        # VIN
        m = re.search(
            r"(?:VIN|[Nn]um[eé]ro\s*(?:d.)?identification)\s*[:\s]*([A-HJ-NPR-Z0-9]{17})",
            text
        )
        if m:
            data["vin"] = m.group(1)

        # Signatures
        data["signatures_vendeur"] = bool(
            re.search(r"[Ss]ignature\s*(?:du\s*)?vendeur", text)
        )
        data["signature_acheteur"] = bool(
            re.search(r"[Ss]ignature\s*(?:de\s*l.)?\s*acqu[eé]reur", text)
        )

        # Numéro de formule
        m = re.search(r"[Ff]ormule\s*[:\s]*(\d{10,})", text)
        if m:
            data["numero_formule"] = m.group(1)

        # SIRET vendeur (tampon)
        m = re.search(r"(?:SIRET|siret)\s*[:\s]*(\d{14})", text)
        if m:
            data["vendeur_siret"] = m.group(1)
            data["tampon_siret"] = True

        return ExtractionResult(
            success=bool(data.get("acheteur_nom") or data.get("vendeur_nom")),
            data=data,
            confidence=0.6,
            raw_text=text[:500],
        )

    # ─── Interface BaseExtractor ───

    def get_extraction_prompt(self) -> str:
        return """
Tu es un expert en lecture de certificats de cession de véhicules (Cerfa 15776).
Extrais : vendeur (nom, SIRET), acquéreur (nom), date de cession, VIN,
immatriculation, présence des signatures.
"""

    def get_json_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "vendeur_nom": {"type": ["string", "null"]},
                "vendeur_siret": {"type": ["string", "null"]},
                "acheteur_nom": {"type": ["string", "null"]},
                "date_cession": {"type": ["string", "null"]},
                "vin": {"type": ["string", "null"]},
                "immatriculation": {"type": ["string", "null"]},
                "signatures_vendeur": {"type": "boolean"},
                "signature_acheteur": {"type": "boolean"},
            }
        }

    def parse_response(self, raw_response: str) -> ExtractedCession:
        raise NotImplementedError

    def extract(self, ocr_text: str) -> ExtractionResult:
        return self.extract_from_ocr_text(ocr_text)
