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
        # TODO: parser le JSON et instancier ExtractedAssurance
        raise NotImplementedError

    def extract(self, ocr_text: str) -> ExtractionResult:
        # TODO: appel LLM + parse
        # TODO: vérification présence RC dans les garanties
        # TODO: si VIN présent : nettoyage (espaces, tirets)
        raise NotImplementedError
