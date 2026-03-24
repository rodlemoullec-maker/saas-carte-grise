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
        # TODO: parser le JSON de la réponse LLM et instancier ExtractedCOC
        raise NotImplementedError

    def extract(self, ocr_text: str) -> ExtractionResult:
        # TODO: appel LLM + parse + validation
        # TODO: post-traitement spécifique COC :
        #   - normalisation énergie (table de mapping)
        #   - nettoyage VIN (suppression espaces/tirets, uppercase)
        #   - détection langue étrangère → flag pour traduction
        raise NotImplementedError
