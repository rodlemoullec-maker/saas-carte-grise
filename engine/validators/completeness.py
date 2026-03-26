"""
Validateur de complétude documentaire (V-01 à V-10, V-36).

Vérifie que tous les documents obligatoires sont présents selon le type
de flux (VN ou VO) et les cas particuliers (personne morale, mineur, etc.).
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from engine.validators.base import BaseValidator, ValidationLevel, ValidationResult


class FlowType(str, Enum):
    VN = "VN"  # Véhicule neuf — première immatriculation
    VO = "VO"  # Véhicule d'occasion — changement de titulaire


@dataclass
class DossierDocuments:
    """Représente les documents présents dans un dossier (booléens de présence)."""
    # Identité acheteur
    cni_ou_passeport: bool = False          # D-07 / D-08
    permis: bool = False                     # D-10
    justif_domicile: bool = False            # D-11 à D-15
    titre_sejour: bool = False               # D-09

    # Formulaires
    cerfa_cg: bool = False                   # D-01 (VN) / D-02 (VO)
    mandat: bool = False                     # D-04
    cerfa_cession: bool = False              # D-03 (VO)

    # Véhicule
    coc: bool = False                        # D-16 (VN)
    cg_barree: bool = False                  # D-17 (VO)
    controle_technique: bool = False         # D-18 (VO si applicable)
    assurance: bool = False                  # D-19
    code_cession_ants: bool = False          # D-20 (VO)
    da: bool = False                         # D-05 (VO)
    recepisse_da: bool = False               # D-21 (VO)
    histovec: bool = False                   # D-22 (VO Phase 0)

    # Spéciaux
    kbis: bool = False                       # D-23 (PM)
    cni_representant_legal: bool = False     # D-24 (PM)
    livret_famille: bool = False             # D-26
    autorisation_parentale: bool = False     # D-27 (mineur)
    attestation_identite_pro: bool = False   # D-31

    # Contexte
    is_personne_morale: bool = False
    is_mineur: bool = False
    is_etranger: bool = False
    ct_dispense: bool = False                # < 4 ans voiture / < 5 ans moto
    ct_volontaire: bool = False              # CT passé sur véhicule dispensé → obligatoire
    pro_habilite_siv: bool = False           # Pro habilité → code cession non requis
    cg_perdue: bool = False                  # CG perdue → D-06 remplace D-17


# Définition des documents obligatoires par V-rule
_COMMON_REQUIRED = [
    ("V-01", "cni_ou_passeport", "CNI ou passeport absent (D-07/D-08)"),
    ("V-03", "justif_domicile", "Justificatif de domicile absent (D-11 à D-15)"),
    ("V-04", "cerfa_cg", "Cerfa demande de CG absent (D-01/D-02)"),
    ("V-05", "mandat", "Mandat de procuration absent (D-04)"),
    ("V-09", "assurance", "Attestation d'assurance véhicule absente (D-19)"),
    ("V-38", "attestation_identite_pro", "Attestation vérification identité pro absente (D-31)"),
]

_VN_REQUIRED = [
    ("V-10", "coc", "Certificat de conformité (COC) absent (D-16)"),
]

_VO_REQUIRED = [
    ("V-06", "cerfa_cession", "Cerfa de cession absent (D-03)"),
    ("V-07", "cg_barree", "Carte grise barrée absente (D-17)"),
    ("V-36", "da", "Déclaration d'Achat (DA) absente (D-05)"),
    ("V-36", "recepisse_da", "Récépissé DA absent (D-21)"),
]


class CompletenessValidator(BaseValidator):
    """
    Vérifie la complétude documentaire d'un dossier.

    V-01 : CNI absente
    V-02 : Permis absent (sauf PM)
    V-03 : Justif domicile absent
    V-04 : Cerfa CG absent
    V-05 : Mandat absent
    V-06 : Cerfa cession absent (VO)
    V-07 : CG barrée absente (VO, sauf perte)
    V-08 : CT absent (VO, sauf dispense)
    V-09 : Assurance absente
    V-10 : COC absent (VN)
    V-36 : DA / récépissé DA absent (VO)
    """

    def validate(self, flow: FlowType, docs: DossierDocuments) -> ValidationResult:
        result = ValidationResult(valid=True)

        # Documents communs VN + VO
        for code, attr, message in _COMMON_REQUIRED:
            if not getattr(docs, attr):
                result.add_error(
                    code=code,
                    message=message,
                    level=ValidationLevel.BLOCKING,
                    field=attr,
                    correction_action="Demander au pro ou au client de fournir le document manquant",
                )

        # V-02 : Permis — obligatoire SAUF personne morale
        if not docs.is_personne_morale and not docs.permis:
            result.add_error(
                code="V-02",
                message="Permis de conduire absent (D-10) — obligatoire pour le titulaire principal",
                level=ValidationLevel.BLOCKING,
                field="permis",
                correction_action="Fournir le permis de conduire du titulaire principal (C.1)",
            )
        elif docs.is_personne_morale and not docs.permis:
            # PM : permis non requis — pas d'erreur
            pass

        # Documents spécifiques VN
        if flow == FlowType.VN:
            for code, attr, message in _VN_REQUIRED:
                if not getattr(docs, attr):
                    result.add_error(
                        code=code,
                        message=message,
                        level=ValidationLevel.BLOCKING,
                        field=attr,
                        correction_action="Demander le document au constructeur / concessionnaire",
                    )

        # Documents spécifiques VO
        if flow == FlowType.VO:
            for code, attr, message in _VO_REQUIRED:
                value = getattr(docs, attr)
                # CG barrée : pas bloquant si CG perdue (D-06 remplace)
                if attr == "cg_barree" and docs.cg_perdue:
                    result.add_error(
                        code="V-07",
                        message="CG barrée absente (CG perdue — vérifier présence déclaration de perte D-06)",
                        level=ValidationLevel.WARNING,
                        field=attr,
                    )
                    continue
                if not value:
                    result.add_error(
                        code=code,
                        message=message,
                        level=ValidationLevel.BLOCKING,
                        field=attr,
                        correction_action="Demander le document au professionnel",
                    )

            # V-08 : CT — obligatoire sauf dispense (âge véhicule)
            if not docs.ct_dispense or docs.ct_volontaire:
                if not docs.controle_technique:
                    msg = "Contrôle technique absent (D-18)"
                    if docs.ct_volontaire:
                        msg += " — CT volontaire passé sur véhicule dispensé → DEVIENT obligatoire"
                    result.add_error(
                        code="V-08",
                        message=msg,
                        level=ValidationLevel.BLOCKING,
                        field="controle_technique",
                        correction_action="Fournir un CT valide (< 6 mois à la saisie SIV)",
                    )

            # Code cession ANTS : non requis si pro habilité SIV
            if not docs.pro_habilite_siv and not docs.code_cession_ants:
                result.add_error(
                    code="V-18",
                    message="Code de cession ANTS absent (D-20)",
                    level=ValidationLevel.WARNING,
                    field="code_cession_ants",
                    correction_action="Le vendeur doit générer un code de cession sur le site ANTS",
                )

        # Documents personne morale
        if docs.is_personne_morale:
            if not docs.kbis:
                result.add_error(
                    code="V-15",
                    message="Kbis ou avis SIRENE absent (D-23) — requis pour les personnes morales",
                    level=ValidationLevel.BLOCKING,
                    field="kbis",
                    correction_action="Fournir un Kbis de moins de 3 mois ou un avis SIRENE",
                )
            if not docs.cni_representant_legal:
                result.add_error(
                    code="V-01",
                    message="CNI du représentant légal absente (D-24) — requis pour les personnes morales",
                    level=ValidationLevel.BLOCKING,
                    field="cni_representant_legal",
                )

        # Documents mineur
        if docs.is_mineur:
            if not docs.autorisation_parentale:
                result.add_error(
                    code="V-MINEUR-01",
                    message="Autorisation parentale absente (D-27) — obligatoire pour acheteur mineur",
                    level=ValidationLevel.BLOCKING,
                    field="autorisation_parentale",
                )
            if not docs.livret_famille:
                result.add_error(
                    code="V-MINEUR-02",
                    message="Livret de famille absent (D-26) — requis pour établir le lien de parenté",
                    level=ValidationLevel.BLOCKING,
                    field="livret_famille",
                )

        # Documents étranger
        if docs.is_etranger and not docs.titre_sejour:
            result.add_error(
                code="V-13",
                message="Titre de séjour absent (D-09) — obligatoire pour ressortissant hors UE/EEE",
                level=ValidationLevel.BLOCKING,
                field="titre_sejour",
                correction_action="Fournir le titre de séjour en cours de validité",
            )

        return result
