"""Extraction des données d'une carte nationale d'identité ou passeport."""

from src.extraction.base import BaseExtractor


class CNIExtractor(BaseExtractor):

    document_type = "cni"

    prompt_template = """Tu es un expert en documents d'identité français.
Voici le texte OCR extrait d'une carte nationale d'identité ou d'un passeport.
Extrais les champs suivants en JSON strict.

IMPORTANT :
- Extrais exactement les valeurs lues, ne devine pas.
- Si un champ n'est pas lisible ou absent, mets null.
- Les dates sont au format JJ/MM/AAAA.
- Le nom de famille est souvent en majuscules.

Réponds UNIQUEMENT avec le JSON, sans texte avant ni après :

{{
  "type_document": "cni ou passeport",
  "numero": "",
  "nom": "",
  "prenom": "",
  "date_naissance": "",
  "lieu_naissance": "",
  "sexe": "",
  "nationalite": "",
  "date_delivrance": "",
  "date_validite": "",
  "adresse": ""
}}

Texte OCR :
---
{ocr_text}
---"""
