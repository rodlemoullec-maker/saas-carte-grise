"""
Extracteur pour les pièces d'identité (CNI, Passeport).

Deux modes d'extraction :
1. Regex sur texte OCR (rapide, gratuit) — utilisé en premier
2. Appel LLM (Claude) en fallback — pour les cas complexes

Priorité à la MRZ (Machine Readable Zone) quand disponible —
plus fiable que l'OCR visuel pour le nom et prénom.

Note : l'adresse sur la CNI/passeport n'est PAS extraite pour le Cerfa.
L'adresse du Cerfa vient du justificatif de domicile uniquement.
"""
from __future__ import annotations

import re
from datetime import date, datetime
from typing import Any

from engine.extractors.base import BaseExtractor, ExtractionResult
from engine.models.documents import ExtractedIdentite


# Table des grandes villes → département (pour déduire le département de naissance)
COMMUNES_DEPT: dict[str, str] = {
    "PARIS": "75", "MARSEILLE": "13", "LYON": "69", "TOULOUSE": "31",
    "NICE": "06", "NANTES": "44", "MONTPELLIER": "34", "STRASBOURG": "67",
    "BORDEAUX": "33", "LILLE": "59", "RENNES": "35", "REIMS": "51",
    "SAINT-ETIENNE": "42", "LE HAVRE": "76", "TOULON": "83",
    "GRENOBLE": "38", "DIJON": "21", "ANGERS": "49", "NIMES": "30",
    "VILLEURBANNE": "69", "CLERMONT-FERRAND": "63", "LE MANS": "72",
    "AIX-EN-PROVENCE": "13", "BREST": "29", "TOURS": "37",
    "AMIENS": "80", "LIMOGES": "87", "PERPIGNAN": "66",
    "METZ": "57", "BESANCON": "25", "ORLEANS": "45",
    "ROUEN": "76", "MULHOUSE": "68", "CAEN": "14",
    "NANCY": "54", "ARGENTEUIL": "95", "SAINT-DENIS": "93",
    "MONTREUIL": "93", "ROUBAIX": "59", "TOURCOING": "59",
    "AVIGNON": "84", "NANTERRE": "92", "VITRY-SUR-SEINE": "94",
    "POITIERS": "86", "AUBERVILLIERS": "93", "COLOMBES": "92",
    "DUNKERQUE": "59", "VALENCE": "26", "QUIMPER": "29",
    "LORIENT": "56", "VANNES": "56", "SAINT-BRIEUC": "22",
    "CERGY": "95", "PONTOISE": "95", "BAYONNE": "64", "PAU": "64",
    "LA ROCHELLE": "17", "CALAIS": "62", "BOULOGNE-BILLANCOURT": "92",
    "AJACCIO": "2A", "BASTIA": "2B",
    "FORT-DE-FRANCE": "972", "POINTE-A-PITRE": "971",
    "SAINT-DENIS-REUNION": "974", "CAYENNE": "973", "MAMOUDZOU": "976",
}


def deduce_departement(commune: str | None) -> str | None:
    """Déduit le code département à partir de la commune de naissance."""
    if not commune:
        return None
    c = commune.upper().strip()
    if c in COMMUNES_DEPT:
        return COMMUNES_DEPT[c]
    for ville, dept in COMMUNES_DEPT.items():
        if ville in c or c in ville:
            return dept
    return None


def deduce_sexe_from_prenom(prenom: str | None) -> str | None:
    """Déduit le sexe (M/F) depuis le prénom. None si ambigu."""
    if not prenom:
        return None
    p = prenom.strip().split()[0].lower()

    feminine_endings = (
        "elle", "ette", "ine", "ise", "ane", "enne", "onne",
        "ia", "ie", "ee", "ée", "lle", "tte", "nne",
        "ina", "ita", "ola", "yla", "na", "da", "ra",
    )
    masculine_exceptions = {
        "antoine", "maxime", "philippe", "pierre", "andre", "claude",
        "dominique", "camille", "stephane", "patrice", "serge",
        "frederic", "jerome", "herve", "rene", "michele",
        "noe", "moise", "elie", "jesse", "lee", "joe",
    }
    feminine_names = {
        "sarah", "margot", "manon", "marion", "maryam", "fatimah",
        "fleur", "esther", "judith", "ingrid", "agnes", "dolores",
    }
    epicene = {"claude", "dominique", "camille", "eden", "charlie", "andrea", "morgan"}

    if p in epicene:
        return None
    if p in feminine_names:
        return "F"
    if p in masculine_exceptions:
        return "M"
    if any(p.endswith(e) for e in feminine_endings):
        return "F"
    return "M"


def _parse_date(date_str: str) -> date | None:
    """Parse une date dans les formats courants (JJ.MM.AAAA, JJ/MM/AAAA, JJ MM AAAA)."""
    if not date_str:
        return None
    for fmt in ("%d.%m.%Y", "%d/%m/%Y", "%d.%m.%y", "%d/%m/%y"):
        try:
            d = datetime.strptime(date_str.strip(), fmt)
            if d.year > 2050:
                d = d.replace(year=d.year - 100)
            return d.date()
        except ValueError:
            continue
    return None


class IdentiteExtractor(BaseExtractor[ExtractedIdentite]):

    def extract_from_ocr_text(self, ocr_text: str) -> ExtractionResult:
        """
        Extraction par regex sur le texte OCR brut.
        Fonctionne pour CNI française et passeport français.
        """
        text = ocr_text
        data: dict[str, Any] = {}
        type_document = "CNI"

        # ─── MRZ Passeport (source la plus fiable) ───
        m_mrz = re.search(r"P<FRA(.+?)(?:\n|$)", text)
        if m_mrz:
            type_document = "PASSEPORT"
            mrz_content = m_mrz.group(1).strip().rstrip("<")
            parts = mrz_content.split("<<", 1)
            if len(parts) > 0:
                data["nom_naissance"] = parts[0].replace("<", " ").strip()
            if len(parts) > 1:
                data["prenoms_str"] = parts[1].replace("<", " ").strip()

        # ─── MRZ CNI ───
        if not m_mrz:
            m = re.search(r"([A-Z]{2,30})<<([A-Z]{2,30})<", text)
            if m:
                if not data.get("nom_naissance"):
                    data["nom_naissance"] = m.group(1)
                if not data.get("prenoms_str"):
                    data["prenoms_str"] = m.group(2)

        # ─── Nom (texte visuel) ───
        if not data.get("nom_naissance"):
            m = re.search(r"[Nn]om/[Ss]urname\s*\(\d\)\s*\n\s*([A-Z][A-Z\- ]{1,40})", text)
            if m:
                data["nom_naissance"] = m.group(1).strip()
            else:
                m = re.search(r"[Nn]om\s*(?:de\s*naissance)?\s*[:\s]*([A-Z][A-Z\- ]{1,40})", text)
                if m:
                    data["nom_naissance"] = m.group(1).strip()

        # ─── Prénoms (texte visuel) ───
        if not data.get("prenoms_str"):
            m = re.search(r"[Pp]r[eé]noms?\s*/\s*[A-Za-z ]+\s*\(\d\)\s*\n\s*([A-Za-zÀ-ÿ,\- ]{2,60})", text)
            if m:
                data["prenoms_str"] = m.group(1).strip()
            else:
                m = re.search(r"[Pp]r[eé]noms?\s*[:\s]*([A-Za-zÀ-ÿ,\- ]{2,60})", text)
                if m:
                    data["prenoms_str"] = m.group(1).strip()

        # ─── Dates ───
        # Date de naissance
        m = re.search(r"(?:n[eé]e?\s*le|[Dd]ate\s*de\s*naissance)\s*[:/\s]*(\d{2}[./]\d{2}[./]\d{4})", text)
        if m:
            data["date_naissance_str"] = m.group(1)
        else:
            m = re.search(r"[Dd]ate\s*de\s*naissance/.*?\n\s*(\d{2})\s+(\d{2})\s+(\d{4})", text)
            if m:
                data["date_naissance_str"] = f"{m.group(1)}/{m.group(2)}/{m.group(3)}"

        # Date d'expiration
        m = re.search(r"(?:expir|[Dd]ate\s*d.expiration)\S*\s*[:/\s]*(\d{2}[./]\d{2}[./]\d{4})", text, re.IGNORECASE)
        if m:
            data["date_expiration_str"] = m.group(1)
        else:
            m = re.search(r"[Dd]ate\s*d.expiration/.*?\n\s*(\d{2})\s+(\d{2})\s+(\d{4})", text)
            if m:
                data["date_expiration_str"] = f"{m.group(1)}/{m.group(2)}/{m.group(3)}"

        # Date de délivrance
        m = re.search(r"[Dd]ate\s*de\s*d[eé]livrance/.*?\n\s*(\d{2})\s+(\d{2})\s+(\d{4})", text)
        if m:
            data["date_delivrance_str"] = f"{m.group(1)}/{m.group(2)}/{m.group(3)}"
        if not data.get("date_delivrance_str"):
            m = re.search(r"[Dd][eé]livr[eé]e?\s*(?:le)?\s*[:\s]*(\d{2}[./]\d{2}[./]\d{4})", text)
            if m:
                data["date_delivrance_str"] = m.group(1)

        # ─── Autres champs ───
        m = re.search(r"[Ll]ieu\s*(?:de\s*naissance)?\s*[:\s]*([A-Za-zÀ-ÿ\- ]{2,40})", text)
        if m:
            data["lieu_naissance"] = m.group(1).strip()
        if not data.get("lieu_naissance"):
            m = re.search(r"[Ll]ieu\s*de\s*naissance/.*?\n\s*([A-Z][A-Za-zÀ-ÿ\- ]{2,30})", text)
            if m:
                data["lieu_naissance"] = m.group(1).strip()

        m = re.search(r"[Nn]ationalit[eé]\s*[:\s]*([A-Za-zÀ-ÿ\- ]{2,30})", text)
        if m:
            data["nationalite"] = m.group(1).strip()

        # Numéro passeport (2 chiffres + 2 lettres + 5 chiffres)
        m = re.search(r"\b(\d{2}[A-Z]{2}\d{5})\b", text)
        if m:
            data["n_document"] = m.group(1)

        # Numéro CNI
        if not data.get("n_document"):
            m = re.search(r"[Nn]o?\s*[:\s]*(\d{12})", text)
            if m:
                data["n_document"] = m.group(1)

        # Sexe (passeport)
        m = re.search(r"[Ss]exe.*?([MF])\b", text)
        if m:
            data["sexe"] = m.group(1)

        # Classification CNI vs Passeport
        if re.search(r"passeport|passport", text, re.IGNORECASE) or m_mrz:
            type_document = "PASSEPORT"

        # ─── Construction du résultat ───
        prenoms_str = data.get("prenoms_str", "")
        prenoms = [p.strip() for p in prenoms_str.replace(",", " ").split() if p.strip()]

        lieu = data.get("lieu_naissance")
        dept = deduce_departement(lieu)

        sexe = data.get("sexe")
        if not sexe and prenoms:
            sexe = deduce_sexe_from_prenom(prenoms[0])

        date_naissance = _parse_date(data.get("date_naissance_str", ""))
        date_expiration = _parse_date(data.get("date_expiration_str", ""))
        date_delivrance = _parse_date(data.get("date_delivrance_str", ""))

        if not data.get("nom_naissance") or not date_naissance or not date_expiration:
            return ExtractionResult(
                success=False,
                errors=["Champs obligatoires manquants (nom, date naissance, date expiration)"],
                raw_text=text[:500],
            )

        return ExtractionResult(
            success=True,
            data={
                "nom_naissance": data["nom_naissance"],
                "prenoms": prenoms,
                "date_naissance": date_naissance.isoformat(),
                "lieu_naissance": lieu,
                "departement_naissance": dept,
                "sexe": sexe,
                "date_expiration": date_expiration.isoformat(),
                "date_delivrance": date_delivrance.isoformat() if date_delivrance else None,
                "n_document": data.get("n_document", ""),
                "nationalite": data.get("nationalite"),
                "type_document": type_document,
            },
            confidence=0.8 if m_mrz else 0.6,
        )

    # ─── Interface BaseExtractor (LLM — futur) ───

    def get_extraction_prompt(self) -> str:
        return """
Tu es un expert en lecture de documents d'identité officiels (CNI française, passeports, titres de séjour).

RÈGLES IMPORTANTES :
- Priorité aux données de la zone MRZ (lignes de caractères en bas du document)
- Le nom de naissance est différent du nom d'usage (ex: femme mariée)
- Extrais TOUS les prénoms dans l'ordre (le premier est le prénom usuel)
- Ne PAS extraire l'adresse (elle sera prise du justificatif de domicile)
- La date d'expiration : pour une CNI française, vérifie si c'est l'ancienne (10 ans) ou nouvelle version (15 ans)
- La nationalité en code ISO 3 lettres si possible (FRA, DEU, ITA...)
- Ne jamais inventer de données manquantes — retourner null
"""

    def get_json_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "required": ["nom_naissance", "prenoms", "date_naissance", "date_expiration", "n_document", "type_document"],
            "properties": {
                "nom_naissance": {"type": "string"},
                "nom_usage": {"type": ["string", "null"]},
                "prenoms": {"type": "array", "items": {"type": "string"}},
                "date_naissance": {"type": "string", "format": "date"},
                "lieu_naissance": {"type": ["string", "null"]},
                "departement_naissance": {"type": ["string", "null"]},
                "sexe": {"type": ["string", "null"], "enum": ["M", "F", None]},
                "date_expiration": {"type": "string", "format": "date"},
                "date_delivrance": {"type": ["string", "null"], "format": "date"},
                "n_document": {"type": "string"},
                "nationalite": {"type": ["string", "null"]},
                "type_document": {"type": "string", "enum": ["CNI", "PASSEPORT"]},
            }
        }

    def parse_response(self, raw_response: str) -> ExtractedIdentite:
        # TODO: parser le JSON LLM et instancier ExtractedIdentite
        raise NotImplementedError

    def extract(self, ocr_text: str) -> ExtractionResult:
        """Point d'entrée — utilise les regex d'abord, LLM en fallback futur."""
        return self.extract_from_ocr_text(ocr_text)
