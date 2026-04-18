"""
Extracteur pour le Certificat de Conformité (COC).

Le COC est le document pivot pour les véhicules neufs.
Il contient toutes les caractéristiques techniques homologuées.

Champs critiques : VIN, CNIT, marque, énergie, puissance, places, PTAC.
"""
from __future__ import annotations

from typing import Any

from engine.extractors.base import BaseExtractor, ExtractionResult
from engine.models.documents import ExtractedCOC


class COCExtractor(BaseExtractor[ExtractedCOC]):

    def get_extraction_prompt(self) -> str:
        return """
Tu es un expert en lecture de Certificats de Conformité (COC) européens.
Extrais les informations suivantes du document avec la plus grande précision.

RÈGLES IMPORTANTES :
- Le VIN fait toujours 17 caractères alphanumériques (jamais I, O ou Q)
- Le CNIT suit le format : 2 lettres - 3 chiffres - 2 lettres - 2 chiffres - 1 lettre - 3 chiffres
- L'énergie doit être normalisée : essence | diesel | électrique | hybride | hybride_rechargeable | gpl | gnv
- Si un champ est absent du document, retourne null (ne pas inventer)
- Pour la puissance, distingue bien kW (puissance nette) et CV (puissance fiscale)
"""

    def get_json_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "required": ["vin", "marque", "energie"],
            "properties": {
                "vin": {"type": "string"},
                "cnit": {"type": ["string", "null"]},
                "marque": {"type": "string"},
                "modele": {"type": ["string", "null"]},
                "energie": {"type": "string"},
                "carrosserie": {"type": ["string", "null"]},
                "puissance_kw": {"type": ["number", "null"]},
                "puissance_fiscale_cv": {"type": ["integer", "null"]},
                "cylindree_cm3": {"type": ["integer", "null"]},
                "places_assises": {"type": ["integer", "null"]},
                "ptac_kg": {"type": ["integer", "null"]},
                "n_homologation_eu": {"type": ["string", "null"]},
                "constructeur": {"type": ["string", "null"]},
                "date_premiere_immat_ue": {"type": ["string", "null"]},
            }
        }

    def parse_response(self, raw_response: str) -> ExtractedCOC:
        """Parse LLM response (fallback)."""
        import json
        try:
            data = json.loads(raw_response)
            return ExtractedCOC(
                vin=data.get("vin", ""),
                marque=data.get("marque", ""),
                energie=data.get("energie", ""),
            )
        except (json.JSONDecodeError, KeyError):
            raise ValueError(f"Invalid response: {raw_response}")

    def extract(self, ocr_text: str) -> ExtractionResult:
        """Extract COC data from OCR text using regex."""
        return self.extract_from_ocr_text(ocr_text)

    def extract_from_ocr_text(self, ocr_text: str) -> ExtractionResult:
        """Extract COC info via regex."""
        import re

        text = ocr_text
        data: dict[str, Any] = {}

        # ── VIN (17 chars, no I/O/Q — note: S/T/U/V/W/X/Y/Z sont valides) ─────
        m = re.search(r"\bVIN\s*[:/]?\s*([A-HJ-NPR-Z0-9]{17,18})(?![A-HJ-NPR-Z0-9])", text, re.IGNORECASE)
        if not m:
            # Cherche directement une séquence 17-18 alphanum valide (sans I/O/Q)
            m = re.search(r"(?<![A-HJ-NPR-Z0-9])([A-HJ-NPR-Z0-9]{17,18})(?![A-HJ-NPR-Z0-9])", text)
        if m:
            data["vin"] = m.group(1).strip()  # stocke tel quel

        # ── CNIT ──────────────────────────────────────────────────────────────
        # Format : lettres-chiffres-lettres-chiffres-lettre-chiffres (avec tirets)
        m = re.search(
            r"\bCNIT\s*[:/]?\s*([A-Z]{2}[\s\-][A-Z]{2}[\s\-]\d{3}[\s\-]\d{2}[\s\-][A-Z][\s\-]\d{3}[\s\-]\d{3})\b",
            text,
            re.IGNORECASE,
        )
        if m:
            raw = m.group(1)
            # Normalise : "GB-AB-123-45-A-456-789" → "GBAB12345A456789" ou garde le tiret
            data["cnit"] = raw.strip()

        # ── Marque ────────────────────────────────────────────────────────────
        m = re.search(r"(?:[Mm]arque|MARQUE|Make)\s*[:/]?\s*([A-Za-zÀ-ÿ][A-Za-zÀ-ÿ ]{1,29})", text)
        if m:
            data["marque"] = m.group(1).strip()

        # ── Modèle ────────────────────────────────────────────────────────────
        m = re.search(r"(?:[Mm]od[eè]le|MODELE|Model)\s*[:/]?\s*([A-Za-zÀ-ÿ0-9 ]{2,40})", text)
        if m:
            data["modele"] = m.group(1).strip()

        # ── Énergie ───────────────────────────────────────────────────────────
        energie = "autre"
        if re.search(r"[Hh]ybride?\s*[Rr]echargeable|[Pp]lug[\s\-]in", text, re.IGNORECASE):
            energie = "hybride_rechargeable"
        elif re.search(r"[Hh]ybride|[Hh]ybrid|Essence\s*\+\s*[Éé]lectrique", text, re.IGNORECASE):
            energie = "hybride"
        elif re.search(r"[Éé]lectrique|[Ee]lectric", text, re.IGNORECASE):
            energie = "électrique"
        elif re.search(r"[Gg]azole|[Dd]iesel", text, re.IGNORECASE):
            energie = "diesel"
        elif re.search(r"[Ee]ssence|[Pp]etrol|SP95|SP98|E85|sans\s*plomb", text, re.IGNORECASE):
            energie = "essence"
        elif re.search(r"GPL|LPG", text, re.IGNORECASE):
            energie = "gpl"
        elif re.search(r"GNV|CNG", text, re.IGNORECASE):
            energie = "gnv"
        data["energie"] = energie

        # ── Puissance kW ──────────────────────────────────────────────────────
        # "Puissance nette : 110 kW" — on prend la première occurrence
        m = re.search(r"(?:[Pp]uissance\s*(?:nette)?[^:]*)\s*[:/]?\s*(\d{2,4})\s*kW", text)
        if not m:
            m = re.search(r"(\d{2,4})\s*kW", text)
        if m:
            data["puissance_kw"] = int(m.group(1))

        # ── Puissance fiscale CV ───────────────────────────────────────────────
        m = re.search(r"(?:[Pp]uissance\s*(?:fiscale)?[^:]*)\s*[:/]?\s*(\d{1,4})\s*(?:CV|ch|PS)\b", text)
        if not m:
            m = re.search(r"(\d{1,4})\s*(?:CV|ch)\b", text)
        if m:
            data["puissance_fiscale_cv"] = int(m.group(1))

        # ── Cylindrée cm3 ─────────────────────────────────────────────────────
        m = re.search(r"(\d{3,4})\s*cm[³3]", text, re.IGNORECASE)
        if m:
            data["cylindree_cm3"] = int(m.group(1))

        # ── Carrosserie ───────────────────────────────────────────────────────
        m = re.search(r"(?:[Cc]arrosserie|[Bb]ody\s*type|[Tt]ype\s*de\s*carrosserie)\s*[:/]?\s*([A-Za-zÀ-ÿ0-9 \+]{3,40})", text)
        if m:
            data["carrosserie"] = m.group(1).strip()

        # ── Places assises ────────────────────────────────────────────────────
        m = re.search(r"(?:[Nn]ombre\s*(?:de\s*)?)?[Pp]laces?\s*(?:assises?)?\s*[:/]?\s*(\d)", text)
        if m:
            data["places_assises"] = int(m.group(1))

        # ── PTAC kg ───────────────────────────────────────────────────────────
        m = re.search(r"\bPTAC\s*[:/]?\s*(\d{3,4})\s*kg", text, re.IGNORECASE)
        if m:
            data["ptac_kg"] = int(m.group(1))

        # ── N° homologation EU ────────────────────────────────────────────────
        m = re.search(r"[Hh]omologation\s*(?:EU|CE)?\s*[:/]?\s*([A-Z0-9/\-]{5,30})", text)
        if m:
            data["n_homologation_eu"] = m.group(1).strip()

        # ── Validation ────────────────────────────────────────────────────────
        if not data.get("vin"):
            return ExtractionResult(
                success=False,
                errors=["VIN manquant ou illisible"],
                raw_text=text[:300],
            )
        if not data.get("marque"):
            return ExtractionResult(
                success=False,
                errors=["Marque manquante"],
                raw_text=text[:300],
            )

        return ExtractionResult(
            success=True,
            data={
                "vin": data.get("vin"),
                "cnit": data.get("cnit"),
                "marque": data.get("marque"),
                "modele": data.get("modele"),
                "energie": data.get("energie"),
                "carrosserie": data.get("carrosserie"),
                "puissance_kw": data.get("puissance_kw"),
                "puissance_fiscale_cv": data.get("puissance_fiscale_cv"),
                "cylindree_cm3": data.get("cylindree_cm3"),
                "places_assises": data.get("places_assises"),
                "ptac_kg": data.get("ptac_kg"),
                "n_homologation_eu": data.get("n_homologation_eu"),
            },
            confidence=0.85,
        )
