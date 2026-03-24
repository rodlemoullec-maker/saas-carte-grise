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
        # TODO: parser le JSON et instancier ExtractedFacture
        raise NotImplementedError

    def extract(self, ocr_text: str) -> ExtractionResult:
        # TODO: appel LLM + parse + validation
        # TODO: détection facture pro-forma → REJET immédiat
        # TODO: détection correction manuscrite sur document (heuristique image)
        raise NotImplementedError
