"""Extraction des données d'un justificatif de domicile.

Vérifie aussi que le type de justificatif est accepté par l'ANTS
pour une demande de carte grise.
"""

from src.extraction.base import BaseExtractor


class JustificatifExtractor(BaseExtractor):

    document_type = "justificatif_domicile"

    def extract(self, ocr_text: str) -> dict:
        data = super().extract(ocr_text)

        # Vérifier si le type de justificatif est accepté
        type_justif = data.get("type_justificatif", "")
        if type_justif in self.TYPES_ACCEPTES:
            data["justificatif_valide"] = True
        elif type_justif in self.TYPES_REFUSES:
            data["justificatif_valide"] = False
            data["justificatif_motif_refus"] = (
                f"'{type_justif}' n'est pas accepte par l'ANTS pour une carte grise. "
                "Documents acceptes : facture electricite/gaz/eau/telephone/internet, "
                "avis d'imposition, taxe fonciere/habitation, attestation assurance habitation, "
                "quittance de loyer (agence RCS uniquement)."
            )
        else:
            data["justificatif_valide"] = None  # type non identifie

        return data

    # Justificatifs acceptes par l'ANTS pour une carte grise
    TYPES_ACCEPTES = {
        "facture_electricite", "facture_gaz", "facture_eau",
        "facture_telephone", "facture_internet",
        "avis_imposition", "avis_non_imposition",
        "taxe_fonciere", "taxe_habitation",
        "attestation_assurance_habitation",
        "quittance_loyer_agence",
    }

    TYPES_REFUSES = {
        "quittance_loyer_particulier", "bail",
        "fiche_paie", "rib", "autre",
    }

    prompt_template = """Tu es un expert en documents administratifs français.
Voici le texte OCR extrait d'un justificatif de domicile.
Extrais les champs suivants en JSON strict.

IMPORTANT :
- Extrais exactement les valeurs lues, ne devine pas.
- Si un champ n'est pas lisible ou absent, mets null.
- L'adresse complete est la donnee la plus importante.
- Identifie le type de justificatif parmi :
  facture_electricite, facture_gaz, facture_eau, facture_telephone,
  facture_internet, avis_imposition, avis_non_imposition, taxe_fonciere,
  taxe_habitation, attestation_assurance_habitation, quittance_loyer_agence,
  quittance_loyer_particulier, bail, fiche_paie, rib, autre

Reponds UNIQUEMENT avec le JSON, sans texte avant ni apres :

{{
  "type_justificatif": "",
  "nom_titulaire": "",
  "prenom_titulaire": "",
  "adresse_numero": "",
  "adresse_type_voie": "",
  "adresse_nom_voie": "",
  "adresse_complement": "",
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
