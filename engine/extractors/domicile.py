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
        # TODO: parser le JSON et instancier ExtractedDomicile
        raise NotImplementedError

    def extract(self, ocr_text: str) -> ExtractionResult:
        # TODO: appel LLM + parse
        # TODO: normalisation adresse via API BAN (appel dans le validator, pas ici)
        raise NotImplementedError
