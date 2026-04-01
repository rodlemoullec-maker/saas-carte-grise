"""
Génération de Cerfa pré-remplis.

Génère des PDF Cerfa (13749, 13750, 15776, 13757) pré-remplis à partir
des données extraites du dossier. Le pro fait signer au client et
ré-uploade le document signé.

Architecture :
  - Template PDF avec champs de formulaire (AcroForm)
  - Remplissage via pdfrw ou PyPDF2
  - Le Cerfa n'est PAS le document officiel — c'est un outil d'aide
    pour éviter les erreurs de saisie manuscrite
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class CerfaData:
    """Données pour pré-remplir un Cerfa."""
    # Identité titulaire
    nom: str = ""
    prenoms: str = ""
    date_naissance: str = ""  # JJ/MM/AAAA
    lieu_naissance: str = ""
    nationalite: str = "Française"

    # Adresse
    adresse: str = ""
    code_postal: str = ""
    ville: str = ""

    # Véhicule
    vin: str = ""
    immatriculation: str = ""
    marque: str = ""
    modele: str = ""
    type_mine: str = ""
    genre: str = ""
    puissance_cv: str = ""
    energie: str = ""
    date_premiere_immat: str = ""

    # Vendeur (VO)
    vendeur_nom: str = ""
    vendeur_siret: str = ""

    # Mandataire
    mandataire_nom: str = ""
    mandataire_siret: str = ""


# Mapping type Cerfa → numéro Cerfa
CERFA_NUMBERS = {
    "VN": "13749*06",
    "VO": "13750*07",
    "CESSION": "15776*02",
    "MANDAT": "13757*03",
    "DA": "13751*02",
}


class CerfaGenerator:
    """
    Génère un PDF Cerfa pré-rempli.

    Usage :
        data = CerfaData(nom="DUPONT", prenoms="Jean", ...)
        pdf_bytes = CerfaGenerator().generate("VN", data)
    """

    def generate(self, cerfa_type: str, data: CerfaData) -> bytes:
        """
        Génère le PDF pré-rempli.

        Args:
            cerfa_type: "VN", "VO", "CESSION", "MANDAT", "DA"
            data: Données à insérer dans le formulaire

        Returns:
            Contenu du PDF en bytes
        """
        cerfa_number = CERFA_NUMBERS.get(cerfa_type)
        if not cerfa_number:
            raise ValueError(f"Type de Cerfa inconnu : {cerfa_type}")

        # Construire les champs du formulaire
        fields = self._build_fields(cerfa_type, data)

        logger.info(f"[Cerfa] Génération {cerfa_number} avec {len(fields)} champs")

        # TODO: implémenter le remplissage PDF réel
        # Options :
        # 1. pdfrw — léger, bon pour AcroForm
        # 2. PyPDF2 — plus complet mais plus lourd
        # 3. reportlab — génération from scratch (si pas de template)
        #
        # Pour l'instant on retourne un placeholder
        # En production : charger le template depuis data/cerfa_templates/
        # et remplir les champs AcroForm

        return self._generate_placeholder(cerfa_number, fields)

    def generate_from_dossier(self, cerfa_type: str, extracted_docs: Any) -> bytes:
        """
        Raccourci : construit CerfaData depuis les documents extraits
        et génère le PDF.
        """
        data = self._build_cerfa_data(cerfa_type, extracted_docs)
        return self.generate(cerfa_type, data)

    def _build_fields(self, cerfa_type: str, data: CerfaData) -> dict[str, str]:
        """Construit le mapping champ PDF → valeur."""
        common = {
            "nom": data.nom,
            "prenoms": data.prenoms,
            "date_naissance": data.date_naissance,
            "lieu_naissance": data.lieu_naissance,
            "nationalite": data.nationalite,
            "adresse": data.adresse,
            "code_postal": data.code_postal,
            "ville": data.ville,
            "vin": data.vin,
            "marque": data.marque,
        }

        if cerfa_type == "VN":
            common.update({
                "type_mine": data.type_mine,
                "genre": data.genre or "VP",
                "puissance_cv": data.puissance_cv,
                "energie": data.energie,
            })
        elif cerfa_type == "VO":
            common.update({
                "immatriculation": data.immatriculation,
                "date_premiere_immat": data.date_premiere_immat,
            })
        elif cerfa_type == "CESSION":
            common.update({
                "vendeur_nom": data.vendeur_nom,
                "vendeur_siret": data.vendeur_siret,
                "immatriculation": data.immatriculation,
            })
        elif cerfa_type == "MANDAT":
            common.update({
                "mandataire_nom": data.mandataire_nom,
                "mandataire_siret": data.mandataire_siret,
                "immatriculation": data.immatriculation or data.vin,
            })

        return {k: v for k, v in common.items() if v}

    def _build_cerfa_data(self, cerfa_type: str, docs: Any) -> CerfaData:
        """Extrait CerfaData depuis ExtractedDocuments."""
        data = CerfaData()

        if docs.identite:
            data.nom = docs.identite.nom_naissance or ""
            data.prenoms = " ".join(docs.identite.prenoms) if docs.identite.prenoms else ""
            if docs.identite.date_naissance:
                data.date_naissance = docs.identite.date_naissance.strftime("%d/%m/%Y")

        if docs.domicile:
            data.adresse = docs.domicile.adresse_ligne1 or ""
            data.code_postal = docs.domicile.code_postal or ""
            data.ville = docs.domicile.ville or ""

        if docs.coc:
            data.vin = docs.coc.vin or ""
            data.marque = docs.coc.marque or ""
            data.modele = docs.coc.modele or ""
            data.energie = docs.coc.energie or ""
            data.puissance_cv = str(docs.coc.puissance_fiscale_cv or "")
            data.type_mine = docs.coc.cnit or ""

        # CNIT saisi manuellement (prioritaire sur l'extraction COC)
        if hasattr(docs, "cnit_manuel") and docs.cnit_manuel:
            data.type_mine = docs.cnit_manuel

        if docs.cg_barree:
            data.immatriculation = docs.cg_barree.immatriculation or ""

        return data

    def _generate_placeholder(self, cerfa_number: str, fields: dict) -> bytes:
        """
        Génère un PDF placeholder (texte simple).
        En production, remplacer par le remplissage du template PDF réel.
        """
        lines = [
            f"CERFA {cerfa_number} — PRÉ-REMPLI (BROUILLON)",
            "=" * 50,
            "",
            "Ce document est un brouillon pré-rempli.",
            "Il doit être imprimé, signé et re-uploadé dans le portail.",
            "",
            "─── Données pré-remplies ───",
            "",
        ]
        for key, value in fields.items():
            lines.append(f"  {key}: {value}")

        lines.extend([
            "",
            "─── Signatures ───",
            "",
            "  Date : ____/____/________",
            "  Signature titulaire : _____________________",
            "",
        ])

        content = "\n".join(lines)
        # En production : PDF réel. Ici : texte brut
        return content.encode("utf-8")
