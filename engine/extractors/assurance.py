"""
Extracteur pour l'attestation d'assurance.

Gère les attestations définitives et les assurances provisoires (sans VIN).
La RC minimum est obligatoire — vérifier la présence de cette garantie.
"""
from __future__ import annotations

from typing import Any

from engine.extractors.base import BaseExtractor, ExtractionResult
from engine.models.documents import ExtractedAssurance


class AssuranceExtractor(BaseExtractor[ExtractedAssurance]):

    def get_extraction_prompt(self) -> str:
        return """
Tu es un expert en lecture d'attestations d'assurance automobile françaises.

RÈGLES IMPORTANTES :
- Le VIN peut être absent (assurance provisoire avant immatriculation) — retourner null dans ce cas
- La RC (Responsabilité Civile) doit être identifiée parmi les garanties
- La date d'effet est la date de début de couverture
- La date d'échéance est la date de fin (souvent 1 an)
- Détermine si c'est une assurance provisoire (flag booléen)
- Le numéro de contrat est distinct du numéro de carte verte
- L'assuré principal est la personne physique responsable (pas forcément le propriétaire)
"""

    def get_json_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "required": ["nom_assure", "prenom_assure", "date_effet", "date_echeance"],
            "properties": {
                "nom_assure": {"type": "string"},
                "prenom_assure": {"type": "string"},
                "vin": {"type": ["string", "null"]},
                "marque": {"type": ["string", "null"]},
                "modele": {"type": ["string", "null"]},
                "n_contrat": {"type": ["string", "null"]},
                "date_effet": {"type": "string", "format": "date"},
                "date_echeance": {"type": "string", "format": "date"},
                "compagnie": {"type": ["string", "null"]},
                "garanties": {"type": "array", "items": {"type": "string"}},
                "rc_incluse": {"type": "boolean"},
                "provisoire": {"type": "boolean"},
            }
        }

    def parse_response(self, raw_response: str) -> ExtractedAssurance:
        """Parse LLM response (fallback)."""
        import json
        try:
            data = json.loads(raw_response)
            return ExtractedAssurance(
                nom_assure=data.get("nom_assure", ""),
                prenom_assure=data.get("prenom_assure", ""),
                date_effet=data.get("date_effet"),
                date_echeance=data.get("date_echeance"),
            )
        except (json.JSONDecodeError, KeyError):
            raise ValueError(f"Invalid response: {raw_response}")

    def extract(self, ocr_text: str) -> ExtractionResult:
        """Extract insurance data from OCR text."""
        return self.extract_from_ocr_text(ocr_text)

    def extract_from_ocr_text(self, ocr_text: str) -> ExtractionResult:
        """Extract insurance info via regex."""
        import re
        from datetime import datetime

        text = ocr_text
        data: dict[str, Any] = {}

        # ── Nom assuré ────────────────────────────────────────────────────────
        # "Assuré : DUPONT Jean-Marie" → on ne veut que le NOM (tout caps)
        # "Nom : DUPONT" + "Prénom : Jean-Marie"
        m_nom = re.search(r"(?:[Nn]om|NOM)\s*[:/]\s*([A-ZÀÂÄÉÈÊËÎÏÔÙÛÜ]{2,30})", text)
        m_prenom = re.search(r"(?:[Pp]r[eé]nom|PRENOM)\s*[:/]\s*([A-Za-zÀ-ÿ][A-Za-zÀ-ÿ\- ]{1,40})", text)

        if m_nom:
            data["nom_assure"] = m_nom.group(1).strip()
        if m_prenom:
            data["prenom_assure"] = m_prenom.group(1).strip()

        # Fallback "Assuré : MARTIN Sophie" → split sur premier espace
        if not data.get("nom_assure"):
            m = re.search(
                r"[Aa]ssur[eé]\s*[:/]\s*([A-ZÀÂÄÉÈÊËÎÏÔÙÛÜ]{2,30})(?:\s+([A-Za-zÀ-ÿ][A-Za-zÀ-ÿ\- ]{1,30}))?",
                text,
            )
            if m:
                data["nom_assure"] = m.group(1).strip()
                if m.group(2) and not data.get("prenom_assure"):
                    data["prenom_assure"] = m.group(2).strip()
        # Dernier fallback : "Nom : MARTIN" seul (sans label Assuré)
        if not data.get("nom_assure"):
            m = re.search(r"^\s*(?:[Nn]om|NOM)\s*:\s*([A-ZÀÂÄÉÈÊËÎÏÔÙÛÜ]{2,30})", text, re.MULTILINE)
            if m:
                data["nom_assure"] = m.group(1).strip()

        # ── VIN ───────────────────────────────────────────────────────────────
        m = re.search(r"\bVIN\s*(?:du\s*v[eé]hicule)?\s*[:/]?\s*([A-HJ-NPR-Z0-9]{17,18})(?![A-HJ-NPR-Z0-9])", text, re.IGNORECASE)
        if not m:
            m = re.search(r"(?<![A-HJ-NPR-Z0-9])([A-HJ-NPR-Z0-9]{17,18})(?![A-HJ-NPR-Z0-9])", text)
        if m:
            data["vin"] = m.group(1).strip()  # stocke tel quel
        else:
            data["vin"] = None

        # ── Marque / Modèle ───────────────────────────────────────────────────
        # "Marque/Modèle : Non renseigné" → None (on vérifie la valeur capturée)
        m = re.search(r"[Mm]arque\s*(?:v[eé]hicule)?\s*[:/]?\s*([A-Za-zÀ-ÿ][A-Za-zÀ-ÿ ]{1,29})", text)
        if m:
            val = m.group(1).strip()
            # Rejette si "Non renseigné", "N/A", ou si la valeur est "Modèle" (artefact "Marque/Modèle")
            if not re.match(r"^(?:[Nn]on\s*[Rr]enseign[eé]|N/?A|Mod[eè]le)", val):
                data["marque"] = val

        m = re.search(r"[Mm]od[eè]le\s*[:/]?\s*([A-Za-zÀ-ÿ0-9 \-\.]{2,40})", text)
        if m:
            val = m.group(1).strip()
            if not re.match(r"^(?:[Nn]on\s*[Rr]enseign[eé]|N/?A)", val):
                data["modele"] = val

        # ── Numéro de contrat ─────────────────────────────────────────────────
        m = re.search(
            r"(?:N[°º]?\s*[Cc]ontrat|[Cc]ontrat\s*(?:n[°º]?|provisoire\s*n[°º]?))\s*[:/]?\s*([A-Z0-9\-]{5,20})",
            text,
        )
        if m:
            data["n_contrat"] = m.group(1).strip()

        # ── Compagnie d'assurance ─────────────────────────────────────────────
        m = re.search(
            r"(?:[Ee]ntreprise\s*d.[Aa]ssurance|[Ss]oci[eé]t[eé]\s*d.[Aa]ssurance|[Aa]ssureur|[Cc]ompagnie)\s*[:/]?\s*([A-Za-zÀ-ÿ][A-Za-zÀ-ÿ0-9 \-\.]{2,40})",
            text,
        )
        if not m:
            # "AXA Assurances France" — première ligne non vide après le label
            for compagnie in ["AXA", "Allianz", "MAIF", "Maif", "MAAF", "Generali", "GENERALI", "Axa", "MFA", "GMF"]:
                if re.search(compagnie, text):
                    data["compagnie"] = compagnie
                    break
        if m:
            data["compagnie"] = m.group(1).strip()

        # ── Dates (effet / échéance) ──────────────────────────────────────────
        def _parse(ds: str) -> str | None:
            for fmt in ("%d.%m.%Y", "%d/%m/%Y"):
                try:
                    return datetime.strptime(ds, fmt).strftime("%Y-%m-%d")
                except ValueError:
                    pass
            return None

        # Date d'effet
        m = re.search(
            r"(?:[Ee]ffet\s*(?:de\s*(?:la\s*)?couverture)?|[Dd]ate\s*(?:d['.\s])?[Ee]ffet|[Dd]ate\s*d.effet)\s*[:/]?\s*(\d{1,2}[./]\d{1,2}[./]\d{4})",
            text,
        )
        if m:
            data["date_effet"] = _parse(m.group(1))

        # Date d'échéance — cherche la plus tardive si plusieurs lignes
        echéances = re.findall(
            r"(?:[Éé]ch[eé]ance|[Vv]al(?:ide|able?|id?)\s*jusqu.au|[Vv]alid\s*until|[Ee]xpir(?:ation|e))\s*[:/]?\s*(\d{1,2}[./]\d{1,2}[./]\d{4})",
            text,
            re.IGNORECASE,
        )
        if echéances:
            # Prend la dernière date (la plus tardive pour couvertures multi-ans)
            parsed = [_parse(e) for e in echéances if _parse(e)]
            if parsed:
                data["date_echeance"] = max(parsed)

        # Fallback : les dates "01.01.2026 - 31.12.2026" en séquences
        if not data.get("date_effet") or not data.get("date_echeance"):
            pairs = re.findall(
                r"(\d{1,2}[./]\d{1,2}[./]\d{4})\s*[-–]\s*(\d{1,2}[./]\d{1,2}[./]\d{4})",
                text,
            )
            if pairs:
                if not data.get("date_effet"):
                    data["date_effet"] = _parse(pairs[0][0])
                if not data.get("date_echeance"):
                    # La date de fin la plus tardive
                    ends = [_parse(p[1]) for p in pairs if _parse(p[1])]
                    if ends:
                        data["date_echeance"] = max(ends)

        # ── RC incluse ────────────────────────────────────────────────────────
        rc_incluse = bool(
            re.search(r"[Rr]esponsabilit[eé]\s*[Cc]ivile|RC\b|Liability", text)
        )

        # ── Provisoire ────────────────────────────────────────────────────────
        # Provisoire = mot "provisoire" OU VIN explicitement "Non renseigné"
        vin_explicitement_absent = bool(
            re.search(r"VIN[^\n]*(?:[Nn]on\s*[Rr]enseign[eé]|N/A|null|\[\])", text)
        )
        provisoire = bool(
            re.search(r"[Pp]rovisoire|provisional", text, re.IGNORECASE)
            or vin_explicitement_absent
        )

        # ── Détection document : l'assurance est juste reconnue, pas validée ──
        # Le système note sa présence dans le dashboard, sans bloquer le dossier.
        # Mais si le document est totalement illisible (aucun champ extrait), échec.
        detected = bool(
            re.search(
                r"assurance|attestation|contrat|RC\s*incluse|garantie|couverture",
                text,
                re.IGNORECASE,
            )
        )
        has_any_field = bool(
            data.get("nom_assure") or data.get("date_effet") or data.get("date_echeance")
            or data.get("vin") or data.get("n_contrat") or data.get("compagnie")
        )

        # ── Confidence ────────────────────────────────────────────────────────
        confidence = 0.85 if (detected and has_any_field) else (0.40 if detected else 0.10)
        if re.search(r"EXPIR[EÉ]|EXPIRED|\[DATE EXPIRATION DÉPASSÉE\]", text, re.IGNORECASE):
            confidence = 0.30

        return ExtractionResult(
            success=detected and has_any_field,  # False si doc illisible/vide
            errors=[] if (detected and has_any_field) else ["Document d'assurance illisible ou incomplet"],
            data={
                "nom_assure": data.get("nom_assure"),
                "prenom_assure": data.get("prenom_assure"),
                "vin": data.get("vin"),
                "marque": data.get("marque"),
                "modele": data.get("modele"),
                "n_contrat": data.get("n_contrat"),
                "date_effet": data.get("date_effet"),
                "date_echeance": data.get("date_echeance"),
                "compagnie": data.get("compagnie"),
                "rc_incluse": rc_incluse,
                "provisoire": provisoire,
            },
            confidence=confidence,
        )
