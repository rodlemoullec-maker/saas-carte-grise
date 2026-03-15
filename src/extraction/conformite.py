"""Extraction des données d'un certificat de conformité (COC)."""

from src.extraction.base import BaseExtractor


class ConformiteExtractor(BaseExtractor):

    document_type = "certificat_conformite"

    prompt_template = """Tu es un expert en documents automobiles français et européens.
Voici le texte OCR extrait d'un certificat de conformité (COC — Certificate of Conformity).
C'est un document technique délivré par le constructeur qui décrit les caractéristiques
du véhicule. Il peut être en français, anglais ou bilingue.

Extrais les champs suivants en JSON strict.

IMPORTANT :
- Extrais exactement les valeurs lues, ne devine pas.
- Si un champ n'est pas lisible ou absent, mets null.
- Le COC contient des rubriques numérotées (0.1, 0.2, 1, 2, 3, etc.)

Réponds UNIQUEMENT avec le JSON, sans texte avant ni après :

{{
  "numero_reception": "",
  "marque": "",
  "type_commercial": "",
  "denomination_commerciale": "",
  "categorie_vehicule": "",
  "vin": "",
  "genre_national": "",
  "carrosserie": "",
  "energie": "",
  "cylindree": "",
  "puissance_kw": "",
  "puissance_fiscale": "",
  "rapport_puissance_masse": "",
  "nb_places_assises": "",
  "nb_places_debout": "",
  "masse_en_ordre_marche": "",
  "masse_max_charge": "",
  "ptac": "",
  "ptra": "",
  "co2": "",
  "classe_environnementale": "",
  "niveau_sonore": "",
  "type_boite_vitesses": "",
  "nombre_essieux": "",
  "nombre_roues_motrices": ""
}}

Texte OCR :
---
{ocr_text}
---"""
