"""
Extracteur pour la Facture d'achat.

La facture établit la transaction commerciale et lie
le vendeur professionnel à l'acheteur particulier.

Champs critiques : VIN, SIRET vendeur, nom acheteur, date vente, mention "neuf".
"""
from __future__ import annotations

from typing import Any

from engine.extractors.base import BaseExtractor, ExtractionResult
from engine.models.documents import ExtractedFacture


class FactureExtractor(BaseExtractor[ExtractedFacture]):

    def get_extraction_prompt(self) -> str:
        return """
Tu es un expert en lecture de factures de vente de véhicules automobiles en France.
Extrais les informations suivantes avec précision.

RÈGLES IMPORTANTES :
- Le VIN fait exactement 17 caractères (nettoie les espaces et tirets)
- Le SIRET fait 14 chiffres (supprime les espaces)
- La date de vente est la date effective de la transaction (pas la date de livraison)
- Détecte si la mention "véhicule neuf" ou équivalent est présente (oui/non)
- Détecte si c'est une facture pro-forma (flag séparé)
- Le kilométrage à 0 ou non renseigné = véhicule neuf
- Si un champ est absent, retourne null
"""

    def get_json_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "required": ["vin", "marque", "date_vente", "siret_vendeur", "nom_vendeur", "nom_acheteur"],
            "properties": {
                "vin": {"type": "string"},
                "marque": {"type": "string"},
                "modele": {"type": ["string", "null"]},
                "energie": {"type": ["string", "null"]},
                "date_vente": {"type": "string", "format": "date"},
                "prix_ht": {"type": ["number", "null"]},
                "prix_ttc": {"type": ["number", "null"]},
                "tva_taux": {"type": ["number", "null"]},
                "siret_vendeur": {"type": "string"},
                "nom_vendeur": {"type": "string"},
                "adresse_vendeur": {"type": ["string", "null"]},
                "nom_acheteur": {"type": "string"},
                "adresse_acheteur": {"type": ["string", "null"]},
                "n_facture": {"type": ["string", "null"]},
                "kilometrage": {"type": ["integer", "null"]},
                "mention_neuf": {"type": "boolean"},
                "pro_forma": {"type": "boolean"},
            }
        }

    def parse_response(self, raw_response: str) -> ExtractedFacture:
        """Parse LLM response (fallback)."""
        import json
        try:
            data = json.loads(raw_response)
            return ExtractedFacture(
                vin=data.get("vin", ""),
                marque=data.get("marque", ""),
                date_vente=data.get("date_vente"),
                siret_vendeur=data.get("siret_vendeur", ""),
                nom_vendeur=data.get("nom_vendeur", ""),
                nom_acheteur=data.get("nom_acheteur", ""),
            )
        except (json.JSONDecodeError, KeyError):
            raise ValueError(f"Invalid response: {raw_response}")

    def extract(self, ocr_text: str) -> ExtractionResult:
        """Extract invoice data from OCR text."""
        return self.extract_from_ocr_text(ocr_text)

    def extract_from_ocr_text(self, ocr_text: str) -> ExtractionResult:
        """Extract invoice info via regex."""
        import re
        from datetime import datetime

        text = ocr_text
        data: dict[str, Any] = {}

        # ── Pro-forma → rejet immédiat ────────────────────────────────────────
        if re.search(r"pro[\s\-]?forma", text, re.IGNORECASE):
            return ExtractionResult(
                success=False,
                data={"pro_forma": True},
                errors=["Facture pro-forma refusée"],
                raw_text=text[:300],
            )

        # ── VIN (17 chars, pas de I/O/Q — S/V/W/X/Y/Z sont valides) ──────────
        m = re.search(r"\bVIN\s*[:/]?\s*([A-HJ-NPR-Z0-9]{17,18})(?![A-HJ-NPR-Z0-9])", text, re.IGNORECASE)
        if not m:
            m = re.search(r"(?<![A-HJ-NPR-Z0-9])([A-HJ-NPR-Z0-9]{17,18})(?![A-HJ-NPR-Z0-9])", text)
        if m:
            data["vin"] = m.group(1).strip()  # stocke tel quel

        # ── Marque ────────────────────────────────────────────────────────────
        m = re.search(r"[Mm]arque\s*[:/]?\s*([A-Za-zÀ-ÿ][A-Za-zÀ-ÿ ]{1,29})", text)
        if m:
            data["marque"] = m.group(1).strip()

        # ── Modèle ────────────────────────────────────────────────────────────
        m = re.search(r"[Mm]od[eè]le\s*[:/]?\s*([A-Za-zÀ-ÿ0-9 \-]{2,40})", text)
        if m:
            data["modele"] = m.group(1).strip()

        # ── Énergie ───────────────────────────────────────────────────────────
        m = re.search(r"(?:[Éé]nergie|[Ee]ssence|[Cc]arburant|[Ff]uel)\s*[:/]?\s*([A-Za-zÀ-ÿ ]{2,30})", text)
        if not m:
            # "Essence : Diesel" ou ligne seule "Diesel"
            m = re.search(r"[Ee]ssence\s*[:/]?\s*([A-Za-z]{4,})", text)
        if m:
            data["energie"] = m.group(1).strip()
        else:
            # Détection directe
            for energie in ["Hybride", "Diesel", "Essence", "Électrique", "GPL", "GNV"]:
                if re.search(energie, text, re.IGNORECASE):
                    data["energie"] = energie
                    break

        # ── Kilométrage ───────────────────────────────────────────────────────
        m = re.search(r"[Kk]il[oó]m[eé]trage\s*[:/]?\s*(\d[\d\s]*)\s*km", text)
        if not m:
            m = re.search(r"(\d[\d\s]{0,6})\s*km\b", text)
        if m:
            km_str = m.group(1).replace(" ", "").replace("\u202f", "")
            data["kilometrage"] = int(km_str)
            data["mention_neuf"] = int(km_str) < 50
        else:
            data["mention_neuf"] = bool(re.search(r"\bneuf\b|new\b", text, re.IGNORECASE))

        # ── Date de vente ─────────────────────────────────────────────────────
        m = re.search(
            r"(?:[Dd]ate\s*(?:de\s*)?vente|[Dd]ate\s*de\s*vente|[Dd]ate)\s*[:/]?\s*(\d{1,2}[./]\d{1,2}[./]\d{4})",
            text,
        )
        if m:
            date_str = m.group(1)
            for fmt in ("%d.%m.%Y", "%d/%m/%Y"):
                try:
                    d = datetime.strptime(date_str, fmt)
                    data["date_vente"] = d.strftime("%Y-%m-%d")
                    break
                except ValueError:
                    continue

        # ── SIRET (14 chiffres) ───────────────────────────────────────────────
        m = re.search(r"SIRET\s*[:/]?\s*(\d{14})", text, re.IGNORECASE)
        if m:
            data["siret_vendeur"] = m.group(1).strip()

        # ── Nom vendeur ───────────────────────────────────────────────────────
        # Cherche ligne suivant "VENDEUR" ou "PROFESSIONNEL VENDEUR" / "Vendeur :"
        m = re.search(
            r"(?:VENDEUR\s*\n\s*|[Vv]endeur\s*[:/]\s*)([A-Za-zÀ-ÿ][A-Za-zÀ-ÿ0-9 \.\-\,\(\)\']+)",
            text,
        )
        if not m:
            # "Garage NOM" ou "AUTO SERVICES LYON" sur la ligne après "VENDEUR PROFESSIONNEL"
            m = re.search(
                r"(?:VENDEUR\s+PROFESSIONNEL|PROFESSIONNEL\s+VENDEUR)\s*\n\s*([A-Za-zÀ-ÿ][A-Za-zÀ-ÿ0-9 \.\-]+)",
                text,
            )
        if m:
            nom = m.group(1).strip()
            # Arrêter avant le SIRET ou l'adresse
            nom = re.split(r"\n|SIRET", nom)[0].strip()
            data["nom_vendeur"] = nom

        # ── Nom acheteur ──────────────────────────────────────────────────────
        m = re.search(
            r"(?:[Aa]cheteur|[Aa]cqu[eé]reur|[Cc]lient|[Nn]om)\s*[:/]\s*([A-ZÀÂÄÉÈÊËÎÏÔÙÛÜ][A-Za-zÀ-ÿ \-]+)",
            text,
        )
        if not m:
            # "Monsieur/Mme : BERNARD Jean-Claude"
            m = re.search(
                r"(?:Monsieur|Madame|Mme|M\.)\s*(?:/\s*(?:Mme|Monsieur))?\s*[:/]?\s*([A-ZÀÂÄÉÈÊËÎÏÔÙÛÜ][A-Za-zÀ-ÿ \-]+)",
                text,
            )
        if not m:
            # "Madame MARTIN Sophie"
            m = re.search(
                r"(?:Madame|Monsieur)\s+([A-ZÀÂÄÉÈÊËÎÏÔÙÛÜ][A-Za-zÀ-ÿ \-]+)",
                text,
            )
        if m:
            nom = m.group(1).strip()
            nom = re.split(r"\n", nom)[0].strip()
            data["nom_acheteur"] = nom

        # ── Prix HT ───────────────────────────────────────────────────────────
        m = re.search(
            r"[Pp]rix\s*(?:[Nn]et\s*)?HT\s*[:/]?\s*(\d[\d\s]*[,.]?\d{0,2})\s*[€EUR]",
            text,
        )
        if not m:
            m = re.search(r"[Pp]rix\s*(?:catalogue|HT)\s*[:/]?\s*:?\s*(\d[\d\s]*[,.]?\d{2})", text)
        if m:
            price_str = m.group(1).replace(" ", "").replace("\u202f", "").replace(",", ".")
            try:
                data["prix_ht"] = float(price_str)
            except ValueError:
                pass

        # ── Prix TTC ──────────────────────────────────────────────────────────
        m = re.search(
            r"[Pp]rix\s*(?:de\s*vente\s*)?TTC\s*[:/]?\s*(\d[\d\s]*[,.]?\d{0,2})\s*[€EUR]",
            text,
        )
        if not m:
            m = re.search(r"[Tt]otal\s*TTC\s*[:/]?\s*(\d[\d\s]*[,.]?\d{2})", text)
        if not m:
            m = re.search(r"[Pp]rix\s*TTC\s*[:/]?\s*(\d[\d\s]*[,.]?\d{2})", text)
        if m:
            price_str = m.group(1).replace(" ", "").replace("\u202f", "").replace(",", ".")
            try:
                data["prix_ttc"] = float(price_str)
            except ValueError:
                pass

        # ── TVA taux ──────────────────────────────────────────────────────────
        m = re.search(r"TVA\s*(\d{1,2})\s*%", text)
        if m:
            data["tva_taux"] = int(m.group(1))

        # ── Numéro de facture ─────────────────────────────────────────────────
        m = re.search(
            r"(?:[Nn][°º]?\s*(?:de\s*)?facture|[Ff]acture\s*n[°º]?|INV[/\-]|FAC[/\-])\s*[:/]?\s*([A-Z0-9][A-Z0-9\-/]{3,19})",
            text,
        )
        if m:
            data["n_facture"] = m.group(1).strip()

        # ── Validation ────────────────────────────────────────────────────────
        if not data.get("vin") or not data.get("siret_vendeur"):
            return ExtractionResult(
                success=False,
                errors=["VIN ou SIRET manquant"],
                raw_text=text[:300],
            )

        # Confidence basse si corrections manuscrites détectées
        confidence = 0.85
        if re.search(r"crossed\s*out|correction|handwritten|barré", text, re.IGNORECASE):
            confidence = 0.40

        return ExtractionResult(
            success=True,
            data={
                "vin": data.get("vin"),
                "marque": data.get("marque"),
                "modele": data.get("modele"),
                "energie": data.get("energie"),
                "kilometrage": data.get("kilometrage"),
                "mention_neuf": data.get("mention_neuf", False),
                "pro_forma": False,
                "date_vente": data.get("date_vente"),
                "siret_vendeur": data.get("siret_vendeur"),
                "nom_vendeur": data.get("nom_vendeur"),
                "nom_acheteur": data.get("nom_acheteur"),
                "prix_ht": data.get("prix_ht"),
                "prix_ttc": data.get("prix_ttc"),
                "tva_taux": data.get("tva_taux"),
                "n_facture": data.get("n_facture"),
            },
            confidence=confidence,
        )
