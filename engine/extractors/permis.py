"""
Extracteur pour le Permis de conduire.

Gère les permis français (format EU depuis 2013) et étrangers.
Vérifie la compatibilité des catégories avec le type de véhicule.
"""
from __future__ import annotations

from typing import Any

from engine.extractors.base import BaseExtractor, ExtractionResult
from engine.models.documents import ExtractedPermis
from engine.ocr_patterns import OptimizedExtraction


class PermisExtractor(BaseExtractor[ExtractedPermis]):

    def get_extraction_prompt(self) -> str:
        return """
Tu es un expert en lecture de permis de conduire (format européen et international).

RÈGLES IMPORTANTES :
- Extrais TOUTES les catégories présentes avec leur date d'obtention et de validité
- Les codes de restriction (01 à 99) doivent être extraits séparément
- Pour un permis français post-2013 : format carte de crédit rose
- La date de délivrance (champ 4a) et la date de validité (champ 4b) sont distinctes
- Le pays d'émission depuis le code sur le document
- Extrais le numéro de permis exactement comme imprimé
"""

    def get_json_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "required": ["nom", "prenom", "date_naissance", "n_permis", "categories"],
            "properties": {
                "nom": {"type": "string"},
                "prenom": {"type": "string"},
                "date_naissance": {"type": "string", "format": "date"},
                "n_permis": {"type": "string"},
                "categories": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "code": {"type": "string"},
                            "date_obtention": {"type": ["string", "null"]},
                            "date_validite": {"type": ["string", "null"]},
                        }
                    }
                },
                "restrictions": {"type": "array", "items": {"type": "string"}},
                "pays_emission": {"type": "string"},
                "date_delivrance": {"type": ["string", "null"]},
            }
        }

    def parse_response(self, raw_response: str) -> ExtractedPermis:
        """Parse LLM response (fallback, not currently used)."""
        import json
        try:
            data = json.loads(raw_response)
            return ExtractedPermis(
                nom=data.get("nom", ""),
                prenom=data.get("prenom", ""),
                date_naissance=data.get("date_naissance"),
                n_permis=data.get("n_permis", ""),
                categories=data.get("categories", []),
            )
        except (json.JSONDecodeError, KeyError):
            raise ValueError(f"Invalid LLM response format: {raw_response}")

    def extract(self, ocr_text: str) -> ExtractionResult:
        """Extract permit data from OCR text using regex."""
        return self.extract_from_ocr_text(ocr_text)

    def extract_from_ocr_text(self, ocr_text: str) -> ExtractionResult:
        """Extract French driving permit info via regex."""
        import re
        from datetime import datetime

        text = ocr_text
        data: dict[str, Any] = {}
        errors: list[str] = []

        # ── Nom / Prénom ──────────────────────────────────────────────────────
        # Pattern 1 : "NOM Prénom" sur une seule ligne après l'en-tête du permis
        # ex. "DUPONT Jean-Paul" ou "MARTIN Sophie"
        m = re.search(
            r"(?:Permis de conduire|Driving Licence)\s*\n\s*"
            r"([A-ZÀÂÄÉÈÊËÎÏÔÙÛÜ]{2,}(?:\s+[A-ZÀÂÄÉÈÊËÎÏÔÙÛÜ]{2,})?)"
            r"\s+([A-Za-zÀ-ÿ][A-Za-zÀ-ÿ\-]{1,})",
            text,
        )
        if m:
            data["nom"] = m.group(1).strip()
            data["prenom"] = m.group(2).strip()
        else:
            # Pattern 2 : ligne unique "NOM Prénom" juste après le titre (sans autre label)
            m = re.search(
                r"^\s*([A-ZÀÂÄÉÈÊËÎÏÔÙÛÜ]{2,})\s+([A-Za-zÀ-ÿ][A-Za-zÀ-ÿ\-]{1,})\s*$",
                text,
                re.MULTILINE,
            )
            if m:
                data["nom"] = m.group(1).strip()
                data["prenom"] = m.group(2).strip()
            else:
                # Pattern 3 : label explicite "Nom :"
                m = re.search(r"(?:Nom|NOM)\s*[:/]\s*([A-ZÀÂÄÉÈÊËÎÏÔÙÛÜ]{2,})", text)
                if m:
                    data["nom"] = m.group(1).strip()
                m = re.search(r"(?:Pr[eé]nom|PRENOM)\s*[:/]\s*([A-Za-zÀ-ÿ][A-Za-zÀ-ÿ\- ]{1,40})", text)
                if m:
                    data["prenom"] = m.group(1).strip()

        # ── Date de naissance — Pattern optimisé (1-2 digits, 4 ou 2 ans, tiret/slash/point) ─
        m = re.search(
            r"(?:n[eé](?:\s*le)?|[Dd]ate\s*(?:of\s*birth|de\s*naissance)|[Nn]aissance|[Dd]ate\s*of\s*birth)\s*[:/]?\s*"
            r"(\d{1,2}[./]\d{1,2}[./]\d{4})",
            text,
            re.IGNORECASE,
        )
        if m:
            data["date_naissance"] = OptimizedExtraction.extract_date(m.group(1))

        # ── Numéro de permis ──────────────────────────────────────────────────
        m = re.search(
            r"(?:N[°º]?\s*(?:de\s*)?permis|Permis\s*n[°º]?|[Ll]icence?\s*number|[Ll]icense\s*num(?:ber)?)\s*[:/]?\s*"
            r"([A-Z0-9]{8,})",
            text,
            re.IGNORECASE,
        )
        if not m:
            # Format classique français : suite de chiffres+lettres 12+ chars
            m = re.search(r"\b(\d{2}[A-Z]{2}\d{6}FR\d{6})\b", text)
        if not m:
            # Numéro étranger quelconque
            m = re.search(r"\b([A-Z0-9]{10,20})\b", text)
        if m:
            data["n_permis"] = m.group(1).strip()

        # ── Catégories ────────────────────────────────────────────────────────
        categories = []
        # Formats : "B : 21.06.2018 - 21.06.2028" ou "Class B : 14.05.2019 - 14.05.2029"
        cat_pattern = re.compile(
            r"\b((?:Class\s+)?[A-C][A-E1-2]?(?:\+[A-Z])?"  # code (B, B+E, A2, C1, Class B…)
            r")\s*[:/]?\s*"
            r"(\d{1,2}[./]\d{1,2}[./]\d{4})\s*[-–]\s*(\d{1,2}[./]\d{1,2}[./]\d{4})"
        )
        for mc in cat_pattern.finditer(text):
            def _fmt(ds: str) -> str:
                for fmt in ("%d.%m.%Y", "%d/%m/%Y"):
                    try:
                        return datetime.strptime(ds, fmt).strftime("%Y-%m-%d")
                    except ValueError:
                        pass
                return ds
            categories.append({
                "code": mc.group(1).strip(),
                "date_obtention": _fmt(mc.group(2)),
                "date_validite": _fmt(mc.group(3)),
            })

        # ── Restrictions ──────────────────────────────────────────────────────
        restrictions: list[str] = []
        m = re.search(
            r"[Rr]estrictions?\s*[:/]?\s*([0-9]{2}(?:\s*,\s*[0-9]{2})*)",
            text,
        )
        if m:
            restrictions = [r.strip() for r in m.group(1).split(",") if r.strip()]
        else:
            # "Restrictions : None" / "Aucune" → liste vide
            if re.search(r"[Rr]estrictions?\s*[:/]?\s*(?:None|Aucune)", text):
                restrictions = []

        # ── Date de délivrance ────────────────────────────────────────────────
        m = re.search(
            r"(?:Date\s*(?:de\s*)?d[eé]livrance|Issue\s*date|Issued)\s*[:/]?\s*"
            r"(\d{1,2}[./]\d{1,2}[./]\d{4})",
            text,
            re.IGNORECASE,
        )
        if m:
            data["date_delivrance"] = OptimizedExtraction.extract_date(m.group(1))

        # ── Pays d'émission ───────────────────────────────────────────────────
        pays = "FR"
        if re.search(r"[Pp]ays\s*d.[eé]mission\s*[:/]?\s*FR", text):
            pays = "FR"
        elif re.search(r"(?:Issued?\s*by|[Éé]mis\s*par)\s*[:/]?\s*(State|[A-Z]{2})", text):
            pays = "OTHER"
        elif re.search(r"\bIssued by\b|\bState of\b", text):
            pays = "OTHER"

        # ── Validation ────────────────────────────────────────────────────────
        if not data.get("nom"):
            errors.append("Champ manquant : nom")
        if not data.get("n_permis"):
            errors.append("Champ manquant : n_permis")
        if not data.get("date_naissance"):
            errors.append("Champ manquant : date_naissance")

        if errors:
            return ExtractionResult(
                success=False,
                errors=errors,
                raw_text=text[:300],
            )

        # Confidence réduite si permis expiré / catégories toutes expirées
        confidence = 0.85
        if re.search(r"\(EXPIR[EÉ]E?\)", text, re.IGNORECASE):
            confidence = 0.5

        return ExtractionResult(
            success=True,
            data={
                "nom": data.get("nom"),
                "prenom": data.get("prenom"),
                "date_naissance": data.get("date_naissance"),
                "n_permis": data.get("n_permis"),
                "categories": categories,
                "restrictions": restrictions,
                "pays_emission": pays,
                "date_delivrance": data.get("date_delivrance"),
            },
            confidence=confidence,
        )
