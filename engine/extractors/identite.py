"""
Extracteur pour les pièces d'identité (CNI, Passeport, Titre de séjour).

Priorité à la lecture MRZ (Machine Readable Zone) quand disponible —
plus fiable que l'OCR visuel pour l'identité.
"""
from __future__ import annotations

from typing import Any

from engine.extractors.base import BaseExtractor, ExtractionResult
from engine.models.documents import ExtractedIdentite


class IdentiteExtractor(BaseExtractor[ExtractedIdentite]):

    def get_extraction_prompt(self) -> str:
        return """
Tu es un expert en lecture de documents d'identité officiels (CNI française, passeports, titres de séjour).

RÈGLES IMPORTANTES :
- Priorité aux données de la zone MRZ (lignes de caractères en bas du document)
- Le nom de naissance est différent du nom d'usage (ex: femme mariée)
- Extrais TOUS les prénoms dans l'ordre (le premier est le prénom usuel)
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
                "date_expiration": {"type": "string", "format": "date"},
                "n_document": {"type": "string"},
                "nationalite": {"type": ["string", "null"]},
                "mrz_ligne1": {"type": ["string", "null"]},
                "mrz_ligne2": {"type": ["string", "null"]},
                "type_document": {"type": "string", "enum": ["CNI", "PASSEPORT", "TITRE_SEJOUR"]},
            }
        }

    def parse_response(self, raw_response: str) -> ExtractedIdentite:
        # TODO: parser le JSON et instancier ExtractedIdentite
        raise NotImplementedError

    def extract(self, ocr_text: str) -> ExtractionResult:
        # TODO: appel LLM + parse
        # TODO: validation MRZ (algorithme ICAO 9303 check digits)
        # TODO: cohérence MRZ vs données visuelles (fraude potentielle si incohérent)
        raise NotImplementedError
