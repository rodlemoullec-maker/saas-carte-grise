"""
Génération du Cerfa 13757 (mandat d'immatriculation) pré-rempli.

Remplit le template PDF AcroForm avec les données du dossier.
Pour le vendeur non habilité, génère 2 mandats :
  - Mandat 1 : client → vendeur (pour constituer le dossier)
  - Mandat 2 : client → agent habilité (pour soumettre au SIV)
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path

from pypdf import PdfReader, PdfWriter

logger = logging.getLogger(__name__)

TEMPLATE_PATH = Path(__file__).parent.parent.parent / "data" / "cerfa_templates" / "cerfa_13757.pdf"


@dataclass
class MandatData:
    """Données pour remplir un mandat 13757."""
    # Mandant (le client qui donne le mandat)
    mandant_nom: str = ""
    mandant_siret: str = ""  # vide si particulier

    # Mandataire (celui qui reçoit le mandat)
    mandataire_nom: str = ""
    mandataire_siret: str = ""

    # Véhicule
    immatriculation: str = ""
    vin: str = ""
    marque: str = ""

    # Opération
    nature_operation: str = "Demande de certificat d'immatriculation"

    # Adresse mandant
    adresse_numero: str = ""
    adresse_type_voie: str = ""
    adresse_nom_voie: str = ""
    adresse_extension: str = ""
    adresse_code_postal: str = ""
    adresse_commune: str = ""
    adresse_pays: str = "FRANCE"

    # Date et lieu
    date_jour: str = ""
    date_mois: str = ""
    date_annee: str = ""
    lieu: str = ""


def fill_mandat(data: MandatData) -> bytes:
    """
    Remplit le template Cerfa 13757 avec les données fournies.
    Retourne les bytes du PDF rempli.
    """
    if not TEMPLATE_PATH.exists():
        raise FileNotFoundError(f"Template 13757 introuvable : {TEMPLATE_PATH}")

    reader = PdfReader(str(TEMPLATE_PATH))
    writer = PdfWriter()
    writer.clone_document_from_reader(reader)

    # Mapping champs PDF ↔ données
    field_values = {
        "txt_IdentitéMandant[0]": data.mandant_nom,
        "num_SIRETMandant[0]": data.mandant_siret,
        "txt_IdentitéMandataire[0]": data.mandataire_nom,
        "num_SIRETMandataire[0]": data.mandataire_siret,
        "txt_MarqueImmatriculation[0]": data.immatriculation,
        "txt_NumVinVéhicule[0]": data.vin,
        "txt_MarqueVéhicule[0]": data.marque,
        "txt_NatureOpération[0]": data.nature_operation,
        "num_VoieAdresse[0]": data.adresse_numero,
        "txt_TypeVoieAdresse[0]": data.adresse_type_voie,
        "txt_NomVoieAdresse[0]": data.adresse_nom_voie,
        "txt_ExtensionAdresse[0]": data.adresse_extension,
        "num_CodePostalAdresse[0]": data.adresse_code_postal,
        "txt_CommuneAdresse[0]": data.adresse_commune,
        "txt_PaysAdresse[0]": data.adresse_pays,
        "num_DateJourDéclaration[0]": data.date_jour,
        "num_DateMoisDéclaration[0]": data.date_mois,
        "num_DateAnnéeDéclaration[0]": data.date_annee,
        "txt_LieuDéclaration[0]": data.lieu,
    }

    # Ne remplir que les champs non-vides
    fields_to_fill = {k: v for k, v in field_values.items() if v}
    writer.update_page_form_field_values(writer.pages[0], fields_to_fill)

    import io
    buf = io.BytesIO()
    writer.write(buf)
    pdf_bytes = buf.getvalue()

    logger.info(f"[Mandat] 13757 généré — {len(fields_to_fill)} champs remplis, {len(pdf_bytes)} bytes")
    return pdf_bytes


def generate_double_mandat(
    client_nom: str,
    client_adresse: dict,
    vendeur_nom: str,
    vendeur_siret: str,
    agent_nom: str,
    agent_siret: str,
    immatriculation: str,
    vin: str,
    marque: str,
    lieu: str = "",
) -> tuple[bytes, bytes]:
    """
    Génère les 2 mandats pour un vendeur non habilité :
      - Mandat 1 : client → vendeur
      - Mandat 2 : client → agent habilité

    Retourne (mandat_vendeur_pdf, mandat_agent_pdf).
    """
    from datetime import datetime
    now = datetime.utcnow()

    base = MandatData(
        mandant_nom=client_nom,
        immatriculation=immatriculation,
        vin=vin,
        marque=marque,
        adresse_numero=client_adresse.get("numero", ""),
        adresse_type_voie=client_adresse.get("type_voie", ""),
        adresse_nom_voie=client_adresse.get("nom_voie", ""),
        adresse_code_postal=client_adresse.get("code_postal", ""),
        adresse_commune=client_adresse.get("commune", ""),
        date_jour=str(now.day).zfill(2),
        date_mois=str(now.month).zfill(2),
        date_annee=str(now.year),
        lieu=lieu,
    )

    # Mandat 1 : client → vendeur
    mandat1_data = MandatData(**{**base.__dict__})
    mandat1_data.mandataire_nom = vendeur_nom
    mandat1_data.mandataire_siret = vendeur_siret
    mandat1_data.nature_operation = "Constitution du dossier d'immatriculation"
    mandat1 = fill_mandat(mandat1_data)

    # Mandat 2 : client → agent
    mandat2_data = MandatData(**{**base.__dict__})
    mandat2_data.mandataire_nom = agent_nom
    mandat2_data.mandataire_siret = agent_siret
    mandat2_data.nature_operation = "Demande de certificat d'immatriculation"
    mandat2 = fill_mandat(mandat2_data)

    logger.info(f"[Mandat] Double mandat généré — vendeur={vendeur_nom}, agent={agent_nom}")
    return mandat1, mandat2
