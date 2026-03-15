"""Extraction des données d'un certificat d'immatriculation (carte grise)."""

from src.extraction.base import BaseExtractor


class CarteGriseExtractor(BaseExtractor):

    document_type = "carte_grise"

    prompt_template = """Tu es un expert en certificats d'immatriculation français (cartes grises).
Voici le texte OCR extrait d'une carte grise. Extrais les champs suivants en JSON strict.

IMPORTANT :
- Extrais exactement les valeurs lues, ne devine pas.
- Si un champ n'est pas lisible ou absent, mets null.
- Le champ A est l'immatriculation (format XX-XXX-XX ou anciennement XXXX XX XX).
- Le champ E est le VIN (17 caractères alphanumériques).
- Le champ D.2 contient le TVV (Type Variante Version) qui sert de CNIT.
- La formule est un code alphanumérique en bas de la carte grise.

Réponds UNIQUEMENT avec le JSON, sans texte avant ni après :

{{
  "A_immatriculation": "",
  "B_date_premiere_immat": "",
  "C1_titulaire_nom": "",
  "C1_titulaire_prenom": "",
  "C3_adresse": "",
  "C4_mention_proprietaire": "",
  "D1_marque": "",
  "D2_type_variante_version": "",
  "D2_1_cnit": "",
  "D3_denomination_commerciale": "",
  "E_vin": "",
  "F1_masse_max_charge": "",
  "F2_ptac": "",
  "G_masse_service": "",
  "G1_ptra": "",
  "I_date_immatriculation": "",
  "J1_genre_national": "",
  "J2_carrosserie_ce": "",
  "J3_carrosserie_nat": "",
  "K_numero_reception": "",
  "P1_cylindree": "",
  "P2_puissance_kw": "",
  "P3_energie": "",
  "P6_puissance_fiscale": "",
  "Q_rapport_puissance_masse": "",
  "S1_nb_places_assises": "",
  "S2_nb_places_debout": "",
  "U1_niveau_sonore": "",
  "V7_co2": "",
  "V9_classe_environnementale": "",
  "X1_date_visite_technique": "",
  "Y1_taxe_regionale": "",
  "Y3_taxe_formation": "",
  "Y4_taxe_co2": "",
  "Y6_taxe_fixe": "",
  "formule": ""
}}

Texte OCR :
---
{ocr_text}
---"""
