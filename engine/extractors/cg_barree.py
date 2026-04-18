"""
Extracteur pour la carte grise barrée (VO — Document D-17).

Le vendeur barre la CG en diagonale, inscrit "Vendu le JJ/MM/AAAA HH:MM"
et signe. Le professionnel vérifie la conformité avant de créer le dossier.
"""
from __future__ import annotations

import re
from datetime import datetime
from typing import Any

from engine.extractors.base import BaseExtractor, ExtractionResult
from engine.models.documents import ExtractedCGBarree


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


class CGBarreeExtractor(BaseExtractor[ExtractedCGBarree]):

    def extract_from_ocr_text(self, ocr_text: str) -> ExtractionResult:
        """Extraction par regex sur le texte OCR brut de la CG barrée."""
        text = ocr_text
        data: dict[str, Any] = {}

        # ── VIN (champ E sur la CG) ───────────────────────────────────────────
        m = VIN_RE.search(text)
        if m:
            data["vin"] = m.group(1)

        # ── Immatriculation ───────────────────────────────────────────────────
        m = IMMAT_RE.search(text)
        if m:
            immat = m.group(1).replace(" ", "-").upper()
            data["immatriculation"] = immat

        # ── Numéro de formule (11 chiffres, champ en haut à droite) ───────────
        m = re.search(r"(?:[Nn][°º]?\s*[Ff]ormule|[Ff]ormule\s*[Nn][°º]?)\s*[:\s]*(\d{11})", text)
        if not m:
            m = re.search(r"\b(\d{11})\b", text)  # fallback : 11 chiffres seuls
        if m:
            data["n_formule"] = m.group(1)

        # ── Titulaire (champ C.1 / C.4.1) ────────────────────────────────────
        m = re.search(
            r"(?:[Tt]itulaire|[Pp]roprietaire|[Nn]om\s*et\s*[Pp]rénom)\s*[:/]?\s*"
            r"([A-ZÀÂÄÉÈÊËÎÏÔÙÛÜ][A-Za-zÀ-ÿ\- ]{2,40})",
            text,
        )
        if m:
            parts = m.group(1).strip().split()
            if len(parts) >= 2:
                data["titulaire_nom"] = parts[0]
                data["titulaire_prenom"] = " ".join(parts[1:])
            else:
                data["titulaire_nom"] = parts[0]

        # ── Date mise en circulation (champ B) ────────────────────────────────
        m = re.search(
            r"(?:[Mm]ise\s*en\s*circulation|[Pp]remi[eè]re\s*immatriculation|[Cc]hamp\s*B)\s*[:/]?\s*"
            r"(\d{1,2}[./]\d{1,2}[./]\d{4})",
            text,
        )
        if m:
            data["date_mise_circulation"] = _parse_date(m.group(1))

        # ── Mention de vente + date + heure ───────────────────────────────────
        # "Vendu le 15/04/2026 à 14:30" ou "Vendu le 15.04.2026 14h30"
        m = re.search(
            r"[Vv][Ee][Nn][Dd][Uu]\s*[Ll][Ee]\s*(\d{1,2}[./]\d{1,2}[./]\d{4})\s*(?:[àÀà]|a|@)?\s*(\d{1,2}[h:]\d{2})?",
            text,
            re.IGNORECASE,
        )
        if m:
            data["date_vente"] = _parse_date(m.group(1))
            if m.group(2):
                data["heure_vente"] = m.group(2).replace("h", ":").strip()

        # ── Acheteur inscrit sur la barre ─────────────────────────────────────
        # "Vendu à DUPONT Jean" ou ligne après la barre
        m = re.search(
            r"[Vv]endu\s*[àa]\s*([A-ZÀÂÄÉÈÊËÎÏÔÙÛÜ][A-Za-zÀ-ÿ\- ]{2,40})",
            text,
        )
        if m:
            parts = m.group(1).strip().split()
            if parts:
                data["acheteur_nom_barre"] = parts[0]
                if len(parts) > 1:
                    data["acheteur_prenom_barre"] = " ".join(parts[1:])

        # ── Marque (champ D.1) ────────────────────────────────────────────────
        m = re.search(r"(?:[Mm]arque|D\.1)\s*[:/]?\s*([A-Za-zÀ-ÿ][A-Za-zÀ-ÿ0-9 \-]{1,25})", text)
        if m:
            data["marque"] = m.group(1).strip()

        # ── Genre national (champ J.1) ────────────────────────────────────────
        m = re.search(r"(?:[Gg]enre|J\.1)\s*[:/]?\s*([A-Z]{2,5})\b", text)
        if m:
            data["genre_national"] = m.group(1)

        # ── Barre diagonale / signatures ──────────────────────────────────────
        data["barre_diagonale"] = bool(
            re.search(r"[Bb][Aa][Rr][Rr][Ee´é]|[Vv][Ee][Nn][Dd][Uu]\s*[Ll][Ee]|VENDU", text)
        )
        # Compte les occurrences de "Signature" ou "[signature]"
        sigs = re.findall(r"[Ss]ignature|\[signature\]|\[SIGN", text)
        data["signatures_count"] = len(sigs)

        # ── Validation ────────────────────────────────────────────────────────
        has_vin = bool(data.get("vin"))
        has_immat = bool(data.get("immatriculation"))
        has_vente = bool(data.get("date_vente"))

        errors = []
        if not has_vin and not has_immat:
            errors.append("VIN et immatriculation manquants")
        if not has_vente:
            errors.append("Date de vente manquante")

        confidence = 0.85 if (has_vin and has_vente) else (0.60 if has_immat else 0.30)

        return ExtractionResult(
            success=bool((has_vin or has_immat) and has_vente),
            data=data,
            errors=errors,
            confidence=confidence,
            raw_text=text[:500],
        )

    # ── Interface BaseExtractor ───────────────────────────────────────────────
    def get_extraction_prompt(self) -> str:
        return "Extrait les données de la carte grise barrée."

    def get_json_schema(self) -> dict[str, Any]:
        return ExtractedCGBarree.model_json_schema()

    def parse_response(self, raw_response: str) -> ExtractedCGBarree:
        return ExtractedCGBarree.model_validate_json(raw_response)

    def extract(self, ocr_text: str) -> ExtractionResult:
        return self.extract_from_ocr_text(ocr_text)
