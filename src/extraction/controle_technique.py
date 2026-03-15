"""Extraction des données d'un contrôle technique."""

from src.extraction.base import BaseExtractor


class ControleTechniqueExtractor(BaseExtractor):

    document_type = "controle_technique"

    prompt_template = """Tu es un expert en documents administratifs français.
Voici le texte OCR extrait d'un procès-verbal de contrôle technique.
Extrais les champs suivants en JSON strict.

IMPORTANT :
- Extrais exactement les valeurs lues, ne devine pas.
- Si un champ n'est pas lisible ou absent, mets null.
- Le résultat est "favorable" (A), "défavorable" (S) ou "défavorable critique" (R).

Réponds UNIQUEMENT avec le JSON, sans texte avant ni après :

{{
  "date_controle": "",
  "date_limite_validite": "",
  "resultat": "favorable, defavorable ou defavorable_critique",
  "immatriculation": "",
  "vin": "",
  "kilometrage": "",
  "centre_controle": "",
  "numero_pv": ""
}}

Texte OCR :
---
{ocr_text}
---"""
