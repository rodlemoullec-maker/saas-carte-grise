"""
Extracteur pour les justificatifs de domicile.

Gère : factures EDF/GDF/eau/téléphone, quittances de loyer,
relevés bancaires, avis d'imposition, attestations d'hébergement.

Point critique : extraire la DATE du document (fraîcheur < 3 mois).
"""
from __future__ import annotations

from typing import Any

from engine.extractors.base import BaseExtractor, ExtractionResult
from engine.models.documents import ExtractedDomicile
from engine.ocr_patterns import OptimizedExtraction


class DomicileExtractor(BaseExtractor[ExtractedDomicile]):

    # Types connus de justificatifs et leurs délais de validité (jours)
    KNOWN_TYPES: dict[str, int] = {
        "facture_electricite": 92,
        "facture_gaz": 92,
        "facture_eau": 92,
        "facture_telephone": 92,
        "facture_internet": 92,
        "quittance_loyer": 92,
        "releve_bancaire": 92,
        "avis_imposition": 365,
        "attestation_hebergement": 0,  # Pas de délai mais pièces complémentaires requises
    }

    def get_extraction_prompt(self) -> str:
        return """
Tu es un expert en lecture de justificatifs de domicile français.
Extrais les informations suivantes avec précision.

RÈGLES IMPORTANTES :
- La date du document est la date d'émission (pas la date de relevé de consommation)
- L'adresse complète doit inclure le numéro de rue, la rue, le code postal et la ville
- Le nom du titulaire tel qu'il apparaît sur le document (peut être un nom d'usage)
- Détermine le type de justificatif parmi : facture_electricite, facture_gaz, facture_eau,
  facture_telephone, facture_internet, quittance_loyer, releve_bancaire, avis_imposition, attestation_hebergement
- L'émetteur est la société/organisme qui a produit le document (ex: EDF, Orange, Crédit Agricole...)
"""

    def get_json_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "required": ["nom_titulaire", "adresse_ligne1", "code_postal", "ville", "date_document"],
            "properties": {
                "nom_titulaire": {"type": "string"},
                "adresse_ligne1": {"type": "string"},
                "adresse_ligne2": {"type": ["string", "null"]},
                "code_postal": {"type": "string"},
                "ville": {"type": "string"},
                "pays": {"type": "string"},
                "date_document": {"type": "string", "format": "date"},
                "type_justificatif": {"type": ["string", "null"]},
                "emetteur": {"type": ["string", "null"]},
            }
        }

    def parse_response(self, raw_response: str) -> ExtractedDomicile:
        """Parse LLM response (fallback)."""
        import json
        try:
            data = json.loads(raw_response)
            return ExtractedDomicile(
                nom_titulaire=data.get("nom_titulaire", ""),
                adresse_ligne1=data.get("adresse_ligne1", ""),
                code_postal=data.get("code_postal", ""),
                ville=data.get("ville", ""),
                date_document=data.get("date_document"),
            )
        except (json.JSONDecodeError, KeyError):
            raise ValueError(f"Invalid response: {raw_response}")

    def extract(self, ocr_text: str) -> ExtractionResult:
        """Extract domicile proof information."""
        return self.extract_from_ocr_text(ocr_text)

    def extract_from_ocr_text(self, ocr_text: str) -> ExtractionResult:
        """Extract address info via regex."""
        import re
        from datetime import datetime

        text = ocr_text
        data: dict[str, Any] = {}

        # ── Type de justificatif ──────────────────────────────────────────────
        type_justificatif = "autre"
        if re.search(r"EDF|[Éé]lectricit[eé]|electricity|Facture d.[eé]lectricit[eé]", text, re.IGNORECASE):
            type_justificatif = "facture_electricite"
        elif re.search(r"GDF|[Gg]az\b|gas\b", text, re.IGNORECASE):
            type_justificatif = "facture_gaz"
        elif re.search(r"\beau\b|water\b", text, re.IGNORECASE):
            type_justificatif = "facture_eau"
        elif re.search(r"[Ii]nternet|[Tt][eé]l[eé]phone|[Ff]acture.*[Tt][eé]l[eé]phone|[Ff]acture.*[Ii]nternet", text, re.IGNORECASE):
            type_justificatif = "facture_internet"
        elif re.search(r"[Qq]uittance|loyer|rent\b", text, re.IGNORECASE):
            type_justificatif = "quittance_loyer"
        elif re.search(r"[Rr]elev[eé].*[Cc]ompte|[Rr]elev[eé]\s+[Dd][Ee]\s+[Cc]ompte|[Bb]ancaire|RELEV", text, re.IGNORECASE):
            type_justificatif = "releve_bancaire"
        elif re.search(r"[Ii]mposition|[Ii]mp[oô]t|[Aa]vis.*[Ii]mposition|AVIS D.IMPOSITION", text, re.IGNORECASE):
            type_justificatif = "avis_imposition"
        elif re.search(r"[Hh][eé]bergement|[Aa]ttestation", text, re.IGNORECASE):
            type_justificatif = "attestation_hebergement"

        # ── Nom titulaire ─────────────────────────────────────────────────────
        # Pattern générique : LABEL [: ] NOM  — stoppe à la 1ère nouvelle ligne
        NOM_RE = r"([A-ZÀÂÄÉÈÊËÎÏÔÙÛÜ][A-Za-zÀ-ÿ\-]+(?:\s+[A-Za-zÀ-ÿ\-]+)*)"
        nom_patterns = [
            # "Titulaire du contrat :\nMOREAU Jean-Claude"
            r"[Tt]itulaire\s*(?:du\s*contrat)?\s*:\s*\n\s*" + NOM_RE,
            # "Titulaire : DUPONT Michel"
            r"[Tt]itulaire\s*:\s*" + NOM_RE,
            # "Locataire : BERNARD Anne-Marie"
            r"[Ll]ocataire\s*:\s*" + NOM_RE,
            # "Client : ROUSSEAU Éric"
            r"[Cc]lient\s*:\s*" + NOM_RE,
            # "Contribuable : MARTIN Sophie"
            r"[Cc]ontribuable\s*:\s*" + NOM_RE,
            # "Je soussigné(e) : LEBLANC François"
            r"[Jj]e\s+soussign[eé][eé]?(?:\(e\))?\s*:\s*" + NOM_RE,
        ]
        for pat in nom_patterns:
            m = re.search(pat, text)
            if m:
                # Stoppe proprement à la fin de la ligne capturée
                val = m.group(1).split('\n')[0].strip()
                data["nom_titulaire"] = val
                break

        # ── Adresse ───────────────────────────────────────────────────────────
        addr_patterns = [
            # "15, rue de la Paix" / "42, avenue Victor Hugo"
            r"(\d{1,4}[,.]?\s*(?:rue|avenue|boulevard|bd|place|allée|route|impasse|chemin|passage|square|cité|résidence|faubourg)[^\n,]{3,50})",
            # "Adresse : 30, route de Versailles"
            r"[Aa]dresse\s*(?:livraison|:)?\s*[:/]?\s*(\d[^\n]{5,60})",
            # "Domicilié(e) à : 10, rue du Faubourg"
            r"[Dd]omicili[eé][eé]?\s*(?:[àa])\s*[:/]?\s*(\d[^\n]{5,60})",
            # "Domicile fiscal : 25, rue de la République"
            r"[Dd]omicile\s*(?:[Ff]iscal|:)\s*[:/]?\s*(\d[^\n]{5,60})",
        ]
        for pat in addr_patterns:
            m = re.search(pat, text, re.IGNORECASE)
            if m:
                addr = m.group(1).strip().rstrip(",")
                # Retire le CP+ville s'il est collé en fin de ligne
                addr = re.sub(r"\s+\d{5}\s+\S.*$", "", addr).strip()
                if len(addr) > 5:
                    data["adresse_ligne1"] = addr
                    break

        # ── Code postal + ville ───────────────────────────────────────────────
        # "75010 PARIS" ou "94200 IVRY-SUR-SEINE"
        m = re.search(r"\b(\d{5})\s+([A-ZÀÂÄÉÈÊËÎÏÔÙÛÜ][A-Z\-]+(?:\s+[A-Z\-]+)*)\b", text)
        if m:
            data["code_postal"] = m.group(1)
            data["ville"] = m.group(2).strip()
        else:
            m = re.search(r"\b(\d{5})\b", text)
            if m:
                data["code_postal"] = m.group(1)

        # ── Émetteur ──────────────────────────────────────────────────────────
        emetteur = None
        if type_justificatif == "facture_electricite":
            emetteur = "EDF"
            if re.search(r"[Éé]ngie|ENGIE", text):
                emetteur = "ENGIE"
        elif type_justificatif == "facture_gaz":
            emetteur = "GDF SUEZ"
        elif type_justificatif == "facture_internet":
            for fai in ["Orange", "SFR", "Bouygues", "Free", "Numericable"]:
                if re.search(fai, text, re.IGNORECASE):
                    emetteur = fai
                    break
            if not emetteur:
                emetteur = "Fournisseur Internet"
        elif type_justificatif == "releve_bancaire":
            for banque in ["Crédit Agricole", "BNP", "Société Générale", "LCL", "Caisse d'Épargne", "La Banque Postale"]:
                if re.search(banque, text, re.IGNORECASE):
                    emetteur = banque
                    break
            if not emetteur:
                emetteur = "Banque"
        data["emetteur"] = emetteur

        # ── Date du document ──────────────────────────────────────────────────
        date_doc = None
        date_patterns = [
            r"[Dd]ate\s*d.[eé]mission\s*[:/]?\s*(\d{1,2}[./]\d{1,2}[./]\d{4})",
            r"[Éé]dition\s*[:/]?\s*(\d{1,2}[./]\d{1,2}[./]\d{4})",
            r"[Aa]vis\s+[eé]mis\s+le\s*[:/]?\s*(\d{1,2}[./]\d{1,2}[./]\d{4})",
            r"[Ss]ign[eé]\s+[àa]\s+\w+,?\s+le\s+(\d{1,2}[./]\d{1,2}[./]\d{4})",
            r"[Dd]ate\s*[:/]?\s*(\d{1,2}[./]\d{1,2}[./]\d{4})",
            r"(\d{1,2}[./]\d{1,2}[./]\d{4})",
        ]
        for pat in date_patterns:
            m = re.search(pat, text)
            if m:
                date_str = m.group(1)
                for fmt in ("%d.%m.%Y", "%d/%m/%Y"):
                    try:
                        d = datetime.strptime(date_str, fmt)
                        date_doc = d.strftime("%Y-%m-%d")
                        break
                    except ValueError:
                        continue
                if date_doc:
                    break

        # ── Validation adresse ────────────────────────────────────────────────
        addr_invalide = (
            not data.get("adresse_ligne1") or data.get("adresse_ligne1") == "N/A"
        )
        cp_invalide = (
            not data.get("code_postal") or data.get("code_postal") in ("????",)
        )
        ville_invalide = data.get("ville") in (None, "INCONNU", "")

        if addr_invalide and cp_invalide and ville_invalide:
            return ExtractionResult(
                success=False,
                errors=["Adresse incomplète ou invalide"],
                raw_text=text[:300],
            )

        # ── Fraîcheur ─────────────────────────────────────────────────────────
        confidence = 0.85
        if date_doc:
            try:
                doc_date = datetime.strptime(date_doc, "%Y-%m-%d")
                days_old = (datetime.now() - doc_date).days
                max_days = 365 if type_justificatif == "avis_imposition" else 92
                if days_old > max_days:
                    return ExtractionResult(
                        success=False,
                        errors=[f"Document trop ancien : {days_old} jours (max {max_days})"],
                        raw_text=text[:300],
                    )
            except ValueError:
                pass

        return ExtractionResult(
            success=True,
            data={
                "nom_titulaire": data.get("nom_titulaire"),
                "adresse_ligne1": data.get("adresse_ligne1"),
                "code_postal": data.get("code_postal"),
                "ville": data.get("ville"),
                "date_document": date_doc,
                "type_justificatif": type_justificatif,
                "emetteur": data.get("emetteur"),
                "pays": "France",
            },
            confidence=confidence,
        )
