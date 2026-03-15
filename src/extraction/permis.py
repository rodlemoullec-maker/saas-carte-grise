"""Extraction des données d'un permis de conduire."""

from src.extraction.base import BaseExtractor


class PermisExtractor(BaseExtractor):

    document_type = "permis_conduire"

    prompt_template = """Tu es un expert en documents d'identité français.
Voici le texte OCR extrait d'un permis de conduire français (format carte).

Le permis contient des catégories (AM, A1, A2, A, B, B1, C, D, etc.)
avec des dates d'obtention pour chacune.

Extrais les champs suivants en JSON strict.

IMPORTANT :
- Extrais exactement les valeurs lues, ne devine pas.
- Si un champ n'est pas lisible ou absent, mets null.
- Les catégories sont listées au verso avec les dates d'obtention.

Réponds UNIQUEMENT avec le JSON, sans texte avant ni après :

{{
  "numero": "",
  "nom": "",
  "prenom": "",
  "date_naissance": "",
  "lieu_naissance": "",
  "date_delivrance": "",
  "date_validite": "",
  "autorite_delivrance": "",
  "categories": [
    {{
      "categorie": "A1, A2, A, B, etc.",
      "date_obtention": "",
      "date_validite": "",
      "restrictions": ""
    }}
  ]
}}

Texte OCR :
---
{ocr_text}
---"""
