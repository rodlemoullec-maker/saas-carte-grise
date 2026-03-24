"""
Extracteur pour le Permis de conduire.

Gère les permis français (format EU depuis 2013) et étrangers.
Vérifie la compatibilité des catégories avec le type de véhicule.
"""
from __future__ import annotations

from typing import Any

from engine.extractors.base import BaseExtractor, ExtractionResult
from engine.models.documents import ExtractedPermis


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
        # TODO: parser le JSON et instancier ExtractedPermis
        raise NotImplementedError

    def extract(self, ocr_text: str) -> ExtractionResult:
        # TODO: appel LLM + parse
        # TODO: détection permis étranger → flag pour vérification règles spécifiques
        raise NotImplementedError
