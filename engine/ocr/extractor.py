"""
Extraction structurée — transforme le texte OCR brut en modèles Pydantic.

Architecture :
  1. OCR provider (Google DocAI / Azure) → texte brut + blocs
  2. Classifier → type de document
  3. Extractor (ce fichier) → modèle Pydantic structuré (ExtractedXxx)

L'extraction utilise des regex métier + LLM (Claude) en fallback
pour les documents complexes ou mal structurés.
"""
from __future__ import annotations

import re
from datetime import date, datetime
from typing import Any

from engine.models.documents import (
    DocumentType,
    ExtractedAssurance,
    ExtractedCerfa,
    ExtractedCGBarree,
    ExtractedCession,
    ExtractedCOC,
    ExtractedCT,
    ExtractedDA,
    ExtractedDomicile,
    ExtractedFacture,
    ExtractedIdentite,
    ExtractedKbis,
    ExtractedPermis,
    ExtractedRecepisseDA,
)
from integrations.ocr_providers.base import OCRResult


class DocumentExtractor:
    """
    Orchestre l'extraction structurée à partir du résultat OCR.

    Usage :
        ocr_result = await ocr_provider.process_document(file_bytes, mime_type)
        doc_type = classifier.classify(ocr_result.full_text)
        extracted = DocumentExtractor().extract(doc_type, ocr_result)
    """

    def extract(self, doc_type: DocumentType, ocr: OCRResult) -> dict[str, Any] | None:
        """
        Extrait les données structurées selon le type de document.

        Retourne un dict sérialisable (modèle Pydantic → .model_dump()).
        Retourne None si le type n'est pas supporté.
        """
        handler = self._handlers.get(doc_type)
        if handler is None:
            return None
        try:
            return handler(self, ocr)
        except Exception:
            return {"error": "extraction_failed", "ocr_confidence": ocr.average_confidence}

    # ──── Extracteurs par type ────────────────────────────────────────────

    def _extract_identite(self, ocr: OCRResult) -> dict:
        """Extrait nom, prénom, DDN, date expiration depuis CNI/passeport."""
        text = ocr.full_text
        data = {
            "nom_naissance": self._find_field(text, r"nom\s*(?:de\s*naissance)?\s*[:\s]*([A-Z\-\s]{2,40})"),
            "prenoms": self._find_list(text, r"pr[eé]noms?\s*[:\s]*([A-Za-zÀ-ÿ\-\s,]{2,60})"),
            "date_naissance": self._find_date(text, r"(?:n[eé]e?\s*le|date\s*de\s*naissance)\s*[:\s]*(\d{2}[./]\d{2}[./]\d{4})"),
            "date_expiration": self._find_date(text, r"(?:expire?\s*le|valide?\s*jusqu|date\s*d.expiration)\s*[:\s]*(\d{2}[./]\d{2}[./]\d{4})"),
            "n_document": self._find_field(text, r"(?:n°|numero)\s*[:\s]*([A-Z0-9]{8,15})"),
            "type_document": "CNI",
            "ocr_confidence": ocr.average_confidence,
        }
        return data

    def _extract_permis(self, ocr: OCRResult) -> dict:
        text = ocr.full_text
        data = {
            "nom": self._find_field(text, r"1\.\s*([A-Z\-\s]{2,40})"),
            "prenom": self._find_field(text, r"2\.\s*([A-Za-zÀ-ÿ\-\s]{2,40})"),
            "date_naissance": self._find_date(text, r"3\.\s*(\d{2}[./]\d{2}[./]\d{4})"),
            "categories": self._find_categories(text),
            "ocr_confidence": ocr.average_confidence,
        }
        return data

    def _extract_coc(self, ocr: OCRResult) -> dict:
        text = ocr.full_text
        data = {
            "vin": self._find_field(text, r"(?:VIN|e)\s*[:\s]*([A-HJ-NPR-Z0-9]{17})"),
            "cnit": self._find_field(text, r"(?:CNIT|D\.2\.1)\s*[:\s]*([A-Z0-9]{6,12})"),
            "marque": self._find_field(text, r"(?:D\.1|marque)\s*[:\s]*([A-Z\-\s]{2,30})"),
            "modele": self._find_field(text, r"(?:D\.3|denomination\s*commerciale)\s*[:\s]*(.{2,50})"),
            "energie": self._find_field(text, r"(?:P\.3|carburant|energie)\s*[:\s]*([A-Za-zÀ-ÿ\s]{2,30})"),
            "puissance_kw": self._find_float(text, r"(?:P\.2|puissance\s*nette)\s*[:\s]*(\d+[.,]?\d*)\s*kW"),
            "puissance_fiscale_cv": self._find_int(text, r"(?:P\.6|puissance\s*administrative)\s*[:\s]*(\d+)\s*CV"),
            "co2_wltp": self._find_float(text, r"(?:V\.7|CO2\s*WLTP)\s*[:\s]*(\d+[.,]?\d*)\s*g"),
            "co2_nedc": self._find_float(text, r"(?:CO2\s*NEDC)\s*[:\s]*(\d+[.,]?\d*)\s*g"),
            "places_assises": self._find_int(text, r"(?:S\.1|places\s*assises)\s*[:\s]*(\d+)"),
            "ptac_kg": self._find_int(text, r"(?:F\.2|PTAC|masse\s*en\s*charge)\s*[:\s]*(\d+)\s*kg"),
            "ocr_confidence": ocr.average_confidence,
        }
        return data

    def _extract_facture(self, ocr: OCRResult) -> dict:
        text = ocr.full_text
        data = {
            "vin": self._find_field(text, r"(?:VIN|n°\s*chassis)\s*[:\s]*([A-HJ-NPR-Z0-9]{17})"),
            "marque": self._find_field(text, r"(?:marque)\s*[:\s]*([A-Za-zÀ-ÿ\-\s]{2,30})"),
            "modele": self._find_field(text, r"(?:modele|mod[eè]le)\s*[:\s]*(.{2,50})"),
            "nom_acheteur": self._find_field(text, r"(?:acqu[eé]reur|acheteur|client)\s*[:\s]*([A-Za-zÀ-ÿ\-\s]{2,60})"),
            "siret_vendeur": self._find_field(text, r"(?:SIRET)\s*[:\s]*(\d[\d\s]{12,16})"),
            "date_vente": self._find_date(text, r"(?:date\s*(?:de\s*)?(?:vente|facture))\s*[:\s]*(\d{2}[./]\d{2}[./]\d{4})"),
            "prix_ttc": self._find_float(text, r"(?:total\s*TTC|montant\s*TTC)\s*[:\s]*(\d[\d\s.,]*)\s*[€E]"),
            "mention_neuf": bool(re.search(r"v[eé]hicule\s*neuf", text, re.IGNORECASE)),
            "ocr_confidence": ocr.average_confidence,
        }
        if data.get("siret_vendeur"):
            data["siret_vendeur"] = re.sub(r"\s", "", data["siret_vendeur"])
        return data

    def _extract_assurance(self, ocr: OCRResult) -> dict:
        text = ocr.full_text
        return {
            "vin": self._find_field(text, r"(?:VIN)\s*[:\s]*([A-HJ-NPR-Z0-9]{17})"),
            "nom_assure": self._find_field(text, r"(?:assur[eé]|souscripteur)\s*[:\s]*([A-Za-zÀ-ÿ\-\s]{2,60})"),
            "compagnie": self._find_field(text, r"(?:compagnie|assureur)\s*[:\s]*(.{2,60})"),
            "date_effet": self._find_date(text, r"(?:date\s*d.effet|effet\s*du)\s*[:\s]*(\d{2}[./]\d{2}[./]\d{4})"),
            "date_echeance": self._find_date(text, r"(?:[eé]ch[eé]ance|expire)\s*[:\s]*(\d{2}[./]\d{2}[./]\d{4})"),
            "rc_incluse": bool(re.search(r"responsabilit[eé]\s*civile|RC", text, re.IGNORECASE)),
            "provisoire": bool(re.search(r"provisoire|temporaire|1\s*mois", text, re.IGNORECASE)),
            "ocr_confidence": ocr.average_confidence,
        }

    def _extract_domicile(self, ocr: OCRResult) -> dict:
        text = ocr.full_text
        return {
            "nom_titulaire": self._find_field(text, r"(?:nom|titulaire|destinataire)\s*[:\s]*([A-Za-zÀ-ÿ\-\s]{2,60})"),
            "adresse_ligne1": self._find_field(text, r"(\d+\s*(?:rue|avenue|boulevard|bd|impasse|chemin|place|all[eé]e)\s+[A-Za-zÀ-ÿ\-\s]{2,80})"),
            "code_postal": self._find_field(text, r"(\d{5})\s+[A-Za-zÀ-ÿ\-\s]"),
            "ville": self._find_field(text, r"\d{5}\s+([A-Za-zÀ-ÿ\-\s]{2,40})"),
            "date_document": self._find_date(text, r"(?:date|du|le)\s*[:\s]*(\d{2}[./]\d{2}[./]\d{4})"),
            "ocr_confidence": ocr.average_confidence,
        }

    def _extract_cg_barree(self, ocr: OCRResult) -> dict:
        text = ocr.full_text
        return {
            "vin": self._find_field(text, r"(?:VIN|E)\s*[:\s]*([A-HJ-NPR-Z0-9]{17})"),
            "immatriculation": self._find_field(text, r"(?:A|immatriculation)\s*[:\s]*([A-Z]{2}[\-\s]?\d{3}[\-\s]?[A-Z]{2})"),
            "n_formule": self._find_field(text, r"(?:formule|Y\.6)\s*[:\s]*(\d{10,11})"),
            "titulaire_nom": self._find_field(text, r"(?:C\.1|titulaire)\s*[:\s]*([A-Za-zÀ-ÿ\-\s]{2,60})"),
            "date_vente": self._find_date(text, r"(?:vendu\s*le)\s*[:\s]*(\d{2}[./]\d{2}[./]\d{4})"),
            "heure_vente": self._find_field(text, r"(?:vendu\s*le\s*\d{2}[./]\d{2}[./]\d{4}\s*[àa]\s*)(\d{1,2}[hH:]\d{2})"),
            "ocr_confidence": ocr.average_confidence,
        }

    def _extract_ct(self, ocr: OCRResult) -> dict:
        text = ocr.full_text
        resultat_raw = self._find_field(text, r"(?:r[eé]sultat)\s*[:\s]*(favorable|d[eé]favorable|critique|A|S|R)")
        resultat_map = {"favorable": "A", "a": "A", "defavorable": "S", "s": "S", "critique": "R", "r": "R"}
        resultat = resultat_map.get((resultat_raw or "").lower(), None)
        return {
            "vin": self._find_field(text, r"(?:VIN)\s*[:\s]*([A-HJ-NPR-Z0-9]{17})"),
            "immatriculation": self._find_field(text, r"(?:immatriculation)\s*[:\s]*([A-Z]{2}[\-\s]?\d{3}[\-\s]?[A-Z]{2})"),
            "date_ct": self._find_date(text, r"(?:date\s*du\s*contr[oô]le|date)\s*[:\s]*(\d{2}[./]\d{2}[./]\d{4})"),
            "resultat": resultat,
            "contre_visite": bool(re.search(r"contre[\-\s]?visite", text, re.IGNORECASE)),
            "ocr_confidence": ocr.average_confidence,
        }

    def _extract_cerfa(self, ocr: OCRResult) -> dict:
        text = ocr.full_text
        return {
            "type_cerfa": self._find_field(text, r"(13749|13750|15776|13757|13751)"),
            "vin": self._find_field(text, r"(?:VIN|E)\s*[:\s]*([A-HJ-NPR-Z0-9]{17})"),
            "immatriculation": self._find_field(text, r"(?:immatriculation)\s*[:\s]*([A-Z]{2}[\-\s]?\d{3}[\-\s]?[A-Z]{2})"),
            "nom_titulaire": self._find_field(text, r"(?:nom|titulaire)\s*[:\s]*([A-Za-zÀ-ÿ\-\s]{2,60})"),
            "adresse": self._find_field(text, r"(?:adresse)\s*[:\s]*(.{5,100})"),
            "code_postal": self._find_field(text, r"(?:code\s*postal)\s*[:\s]*(\d{5})"),
            "ville": self._find_field(text, r"(?:ville|commune)\s*[:\s]*([A-Za-zÀ-ÿ\-\s]{2,40})"),
            "signe": bool(re.search(r"signature|sign[eé]", text, re.IGNORECASE)),
            "rature_detectee": bool(re.search(r"rature|biff[eé]|surcharge", text, re.IGNORECASE)),
            "ocr_confidence": ocr.average_confidence,
        }

    def _extract_cession(self, ocr: OCRResult) -> dict:
        text = ocr.full_text
        return {
            "vin": self._find_field(text, r"(?:VIN)\s*[:\s]*([A-HJ-NPR-Z0-9]{17})"),
            "vendeur_nom": self._find_field(text, r"(?:vendeur)\s*[:\s]*([A-Za-zÀ-ÿ\-\s]{2,60})"),
            "vendeur_siret": self._find_field(text, r"(?:SIRET\s*vendeur)\s*[:\s]*(\d{14})"),
            "acheteur_nom": self._find_field(text, r"(?:acqu[eé]reur|acheteur)\s*[:\s]*([A-Za-zÀ-ÿ\-\s]{2,60})"),
            "date_cession": self._find_date(text, r"(?:date\s*de\s*(?:la\s*)?cession)\s*[:\s]*(\d{2}[./]\d{2}[./]\d{4})"),
            "signatures_vendeur": bool(re.search(r"signature\s*(?:du\s*)?vendeur", text, re.IGNORECASE)),
            "signature_acheteur": bool(re.search(r"signature\s*(?:de\s*l.)?acqu[eé]reur", text, re.IGNORECASE)),
            "tampon_siret": bool(re.search(r"tampon|cachet", text, re.IGNORECASE)),
            "ocr_confidence": ocr.average_confidence,
        }

    def _extract_da(self, ocr: OCRResult) -> dict:
        text = ocr.full_text
        return {
            "vin": self._find_field(text, r"(?:VIN)\s*[:\s]*([A-HJ-NPR-Z0-9]{17})"),
            "immatriculation": self._find_field(text, r"(?:immatriculation)\s*[:\s]*([A-Z]{2}[\-\s]?\d{3}[\-\s]?[A-Z]{2})"),
            "siren_pro": self._find_field(text, r"(?:SIREN)\s*[:\s]*(\d{9})"),
            "siret_pro": self._find_field(text, r"(?:SIRET)\s*[:\s]*(\d{14})"),
            "nom_pro": self._find_field(text, r"(?:acqu[eé]reur|professionnel)\s*[:\s]*(.{2,60})"),
            "vendeur_nom": self._find_field(text, r"(?:vendeur|c[eé]dant)\s*[:\s]*([A-Za-zÀ-ÿ\-\s]{2,60})"),
            "date_achat": self._find_date(text, r"(?:date\s*d.achat|date)\s*[:\s]*(\d{2}[./]\d{2}[./]\d{4})"),
            "ocr_confidence": ocr.average_confidence,
        }

    def _extract_kbis(self, ocr: OCRResult) -> dict:
        text = ocr.full_text
        return {
            "raison_sociale": self._find_field(text, r"(?:d[eé]nomination|raison\s*sociale)\s*[:\s]*(.{2,80})"),
            "siren": self._find_field(text, r"(?:SIREN|RCS)\s*[:\s]*(\d{9})"),
            "siret_siege": self._find_field(text, r"(?:SIRET\s*si[eè]ge)\s*[:\s]*(\d{14})"),
            "representant_nom": self._find_field(text, r"(?:g[eé]rant|pr[eé]sident|dirigeant)\s*[:\s]*([A-Za-zÀ-ÿ\-\s]{2,60})"),
            "date_kbis": self._find_date(text, r"(?:d[eé]livr[eé]\s*le|date)\s*[:\s]*(\d{2}[./]\d{2}[./]\d{4})"),
            "ocr_confidence": ocr.average_confidence,
        }

    # ──── Handler registry ────────────────────────────────────────────────

    _handlers = {
        DocumentType.CNI: _extract_identite,
        DocumentType.PASSEPORT: _extract_identite,
        DocumentType.TITRE_SEJOUR: _extract_identite,
        DocumentType.PERMIS: _extract_permis,
        DocumentType.COC: _extract_coc,
        DocumentType.FACTURE: _extract_facture,
        DocumentType.ASSURANCE: _extract_assurance,
        DocumentType.DOMICILE: _extract_domicile,
        DocumentType.CG_BARREE: _extract_cg_barree,
        DocumentType.CONTROLE_TECHNIQUE: _extract_ct,
        DocumentType.CERFA_VN: _extract_cerfa,
        DocumentType.CERFA_VO: _extract_cerfa,
        DocumentType.CERFA_CESSION: _extract_cession,
        DocumentType.DA: _extract_da,
        DocumentType.MANDAT: _extract_cerfa,  # Structure similaire
        DocumentType.KBIS: _extract_kbis,
    }

    # ──── Helpers regex ───────────────────────────────────────────────────

    @staticmethod
    def _find_field(text: str, pattern: str) -> str | None:
        m = re.search(pattern, text, re.IGNORECASE)
        return m.group(1).strip() if m else None

    @staticmethod
    def _find_date(text: str, pattern: str) -> str | None:
        m = re.search(pattern, text, re.IGNORECASE)
        if m:
            raw = m.group(1).replace("/", ".").replace("-", ".")
            parts = raw.split(".")
            if len(parts) == 3:
                try:
                    return f"{parts[2]}-{parts[1]}-{parts[0]}"  # ISO format
                except Exception:
                    pass
        return None

    @staticmethod
    def _find_float(text: str, pattern: str) -> float | None:
        m = re.search(pattern, text, re.IGNORECASE)
        if m:
            try:
                return float(m.group(1).replace(",", ".").replace(" ", ""))
            except ValueError:
                pass
        return None

    @staticmethod
    def _find_int(text: str, pattern: str) -> int | None:
        m = re.search(pattern, text, re.IGNORECASE)
        if m:
            try:
                return int(m.group(1).replace(" ", ""))
            except ValueError:
                pass
        return None

    @staticmethod
    def _find_list(text: str, pattern: str) -> list[str]:
        m = re.search(pattern, text, re.IGNORECASE)
        if m:
            raw = m.group(1)
            return [p.strip() for p in re.split(r"[,\s]+", raw) if p.strip()]
        return []

    @staticmethod
    def _find_categories(text: str) -> list[str]:
        """Extrait les catégories de permis (AM, A1, A2, A, B, BE, C, CE, D)."""
        cats = re.findall(r"\b(AM|A1|A2|A|BE|B|CE|C|DE|D)\b", text.upper())
        return list(dict.fromkeys(cats))  # Dédoublonner en préservant l'ordre
