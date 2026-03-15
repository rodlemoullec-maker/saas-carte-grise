"""Extraction des données d'un justificatif de domicile."""

from src.extraction.base import BaseExtractor


class JustificatifExtractor(BaseExtractor):

    document_type = "justificatif_domicile"

    prompt_template = """Tu es un expert en documents administratifs français.
Voici le texte OCR extrait d'un justificatif de domicile
(facture EDF, eau, téléphone, internet, avis d'impôt, quittance de loyer).
Extrais les champs suivants en JSON strict.

IMPORTANT :
- Extrais exactement les valeurs lues, ne devine pas.
- Si un champ n'est pas lisible ou absent, mets null.
- L'adresse complète est la donnée la plus importante.
- La date du document sert à vérifier qu'il a moins de 6 mois.

Réponds UNIQUEMENT avec le JSON, sans texte avant ni après :

{{
  "type_justificatif": "facture_edf, facture_eau, facture_telecom, avis_impot, quittance_loyer, autre",
  "nom_titulaire": "",
  "prenom_titulaire": "",
  "adresse_numero": "",
  "adresse_extension": "",
  "adresse_type_voie": "",
  "adresse_nom_voie": "",
  "adresse_complement": "",
  "adresse_lieu_dit": "",
  "adresse_code_postal": "",
  "adresse_ville": "",
  "adresse_complete": "",
  "date_document": "",
  "fournisseur": ""
}}

Texte OCR :
---
{ocr_text}
---"""
