"""Extraction des données d'un certificat de cession (CERFA 15776)."""

from src.extraction.base import BaseExtractor


class CessionExtractor(BaseExtractor):

    document_type = "certificat_cession"

    prompt_template = """Tu es un expert en documents administratifs français.
Voici le texte OCR extrait d'un certificat de cession de véhicule (CERFA 15776).
Extrais les champs suivants en JSON strict.

IMPORTANT :
- Extrais exactement les valeurs lues, ne devine pas.
- Si un champ n'est pas lisible ou absent, mets null.
- Le certificat contient les informations du vendeur et de l'acheteur.
- La date et l'heure de cession sont obligatoires.

Réponds UNIQUEMENT avec le JSON, sans texte avant ni après :

{{
  "vendeur_nom": "",
  "vendeur_prenom": "",
  "vendeur_adresse": "",
  "vendeur_code_postal": "",
  "vendeur_ville": "",
  "acheteur_nom": "",
  "acheteur_prenom": "",
  "acheteur_adresse": "",
  "acheteur_code_postal": "",
  "acheteur_ville": "",
  "acheteur_date_naissance": "",
  "date_cession": "",
  "heure_cession": "",
  "immatriculation": "",
  "vin": "",
  "marque": "",
  "denomination_commerciale": "",
  "kilometrage": "",
  "date_premiere_immat": ""
}}

Texte OCR :
---
{ocr_text}
---"""
