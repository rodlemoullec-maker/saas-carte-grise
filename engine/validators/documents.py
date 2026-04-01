"""
Validateurs de haut niveau pour chaque type de document.

Chaque validateur prend un modèle extrait (ExtractedXxx)
et retourne un ValidationResult complet.
"""
from __future__ import annotations

from datetime import date

from engine.models.documents import (
    ExtractedAssurance,
    ExtractedCOC,
    ExtractedDomicile,
    ExtractedFacture,
    ExtractedIdentite,
    ExtractedPermis,
)
from engine.validators.base import BaseValidator, ValidationLevel, ValidationResult
from engine.validators.dates import AgeValidator, DocumentDateValidator
from engine.validators.siret import SIRETValidator
from engine.validators.vin import VINValidator

# Catégories de permis requises par type de véhicule (code carrosserie EU)
PERMIS_REQUIRED: dict[str, list[str]] = {
    "VP": ["B"],          # Voiture particulière ≤ 3,5T
    "CTTE": ["B"],        # Camionnette ≤ 3,5T
    "MOTO": ["A", "A2"],  # Moto > 125cc
    "CYCLO": ["AM", "B"], # Cyclomoteur ≤ 50cc
    "MOTO_125": ["A1", "A2", "A", "B"],
}


class COCDocumentValidator(BaseValidator):
    def validate(self, coc: ExtractedCOC, reference_date: date | None = None) -> ValidationResult:
        result = ValidationResult(valid=True)

        # VIN obligatoire et valide
        vin_result = VINValidator().validate(coc.vin)
        result.errors.extend(vin_result.errors)
        result.warnings.extend(vin_result.warnings)
        if vin_result.is_blocking:
            result.valid = False

        # Champs obligatoires
        if not coc.marque or not coc.marque.strip():
            result.add_error("COC_MARQUE_MISSING", "Marque absente dans le COC", ValidationLevel.BLOCKING, "marque")

        if not coc.energie or not coc.energie.strip():
            result.add_error("COC_ENERGIE_MISSING", "Énergie absente dans le COC", ValidationLevel.BLOCKING, "energie")

        if coc.places_assises is not None and coc.places_assises < 1:
            result.add_error("COC_PLACES_INVALID", "Nombre de places invalide", ValidationLevel.BLOCKING, "places_assises")

        if coc.puissance_kw is not None and coc.puissance_kw <= 0:
            result.add_error("COC_PUISSANCE_INVALID", "Puissance kW invalide", ValidationLevel.BLOCKING, "puissance_kw")

        if not coc.cnit:
            result.add_error("COC_CNIT_MISSING", "CNIT absent — requis pour SIV", ValidationLevel.WARNING, "cnit",
                             correction_action="Vérifier le COC — contacter constructeur si absent")

        return result


class FactureDocumentValidator(BaseValidator):
    def validate(self, facture: ExtractedFacture, reference_date: date | None = None) -> ValidationResult:
        result = ValidationResult(valid=True)
        ref = reference_date or date.today()

        vin_result = VINValidator().validate(facture.vin)
        result.errors.extend(vin_result.errors)
        result.warnings.extend(vin_result.warnings)
        if vin_result.is_blocking:
            result.valid = False

        siret_result = SIRETValidator().validate(facture.siret_vendeur)
        result.errors.extend(siret_result.errors)
        if siret_result.is_blocking:
            result.valid = False

        if facture.date_vente > ref:
            result.add_error("FACTURE_DATE_FUTURE", "Date de vente dans le futur", ValidationLevel.BLOCKING, "date_vente")

        if not facture.mention_neuf:
            result.add_error("FACTURE_NO_NEUF_MENTION",
                             "Mention 'véhicule neuf' absente sur la facture",
                             ValidationLevel.WARNING, "mention_neuf",
                             correction_action="Vérifier que la facture précise bien qu'il s'agit d'un véhicule neuf")

        if facture.kilometrage is not None and facture.kilometrage > 100:
            result.add_error("FACTURE_KM_SUSPECT",
                             f"Kilométrage ({facture.kilometrage} km) élevé pour un véhicule neuf",
                             ValidationLevel.WARNING, "kilometrage",
                             correction_action="Confirmer si véhicule neuf ou de démonstration")

        return result


class IdentiteDocumentValidator(BaseValidator):
    def validate(self, identite: ExtractedIdentite, reference_date: date | None = None) -> ValidationResult:
        result = ValidationResult(valid=True)

        date_result = DocumentDateValidator().validate("identite", identite.date_expiration, reference_date)
        result.errors.extend(date_result.errors)
        result.warnings.extend(date_result.warnings)
        if date_result.is_blocking:
            result.valid = False

        age_result = AgeValidator().validate(identite.date_naissance, reference_date)
        result.errors.extend(age_result.errors)
        if age_result.is_blocking:
            result.valid = False

        if not identite.nom_naissance or not identite.prenoms:
            result.add_error("IDENTITY_NAME_MISSING", "Nom ou prénom absent", ValidationLevel.BLOCKING, "nom_naissance")

        return result


class DomicileDocumentValidator(BaseValidator):
    def validate(self, domicile: ExtractedDomicile, reference_date: date | None = None) -> ValidationResult:
        result = ValidationResult(valid=True)

        doc_type = domicile.type_justificatif or "facture_electricite"
        date_result = DocumentDateValidator().validate(doc_type, domicile.date_document, reference_date)
        result.errors.extend(date_result.errors)
        result.warnings.extend(date_result.warnings)
        if date_result.is_blocking:
            result.valid = False

        if not domicile.adresse_ligne1 or not domicile.code_postal or not domicile.ville:
            result.add_error("DOMICILE_ADDRESS_INCOMPLETE", "Adresse incomplète", ValidationLevel.BLOCKING, "adresse")

        if domicile.code_postal and len(domicile.code_postal) != 5:
            result.add_error("DOMICILE_CP_INVALID", "Code postal invalide", ValidationLevel.BLOCKING, "code_postal")

        return result


class PermisDocumentValidator(BaseValidator):
    def validate(self, permis: ExtractedPermis, vehicle_type: str | None = None,
                 reference_date: date | None = None) -> ValidationResult:
        result = ValidationResult(valid=True)

        # TODO: vérifier validité de chaque catégorie
        if not permis.categories:
            result.add_error("PERMIS_NO_CATEGORY", "Aucune catégorie de permis détectée", ValidationLevel.BLOCKING, "categories")

        if vehicle_type and vehicle_type in PERMIS_REQUIRED:
            required = PERMIS_REQUIRED[vehicle_type]
            held_codes = {c.code for c in permis.categories}
            if not any(r in held_codes for r in required):
                result.add_error(
                    "PERMIS_CATEGORY_MISMATCH",
                    f"Catégorie insuffisante pour ce véhicule. Requis : {required}, détenu : {list(held_codes)}",
                    ValidationLevel.BLOCKING, "categories",
                    correction_action="Vérifier la catégorie de permis requise pour ce type de véhicule"
                )

        return result


class AssuranceDocumentValidator(BaseValidator):
    def validate(self, assurance: ExtractedAssurance, reference_date: date | None = None) -> ValidationResult:
        result = ValidationResult(valid=True)
        ref = reference_date or date.today()

        effet_result = DocumentDateValidator().validate("assurance_effet", assurance.date_effet, reference_date)
        result.errors.extend(effet_result.errors)
        if effet_result.is_blocking:
            result.valid = False

        echeance_result = DocumentDateValidator().validate("assurance_echeance", assurance.date_echeance, reference_date)
        result.errors.extend(echeance_result.errors)
        if echeance_result.is_blocking:
            result.valid = False

        # Assurance provisoire < 7j restants → WARNING
        if assurance.provisoire:
            jours_restants = (assurance.date_echeance - ref).days
            if 0 < jours_restants < 7:
                result.add_error(
                    "ASSURANCE_PROVISOIRE_EXPIRING",
                    f"Attestation provisoire expire dans {jours_restants} jour(s) — risque avant saisie SIV",
                    ValidationLevel.WARNING, "date_echeance",
                    correction_action="Obtenir l'attestation d'assurance définitive avec VIN avant la saisie SIV"
                )

        if not assurance.rc_incluse:
            result.add_error(
                "ASSURANCE_NO_RC",
                "RC (Responsabilité Civile) non détectée dans les garanties",
                ValidationLevel.BLOCKING, "garanties",
                correction_action="La RC est obligatoire (art. L211-1 Code des assurances)"
            )

        if assurance.vin and len(assurance.vin) > 0 and len(assurance.vin) != 17:
            result.add_error(
                "ASSURANCE_VIN_PARTIAL",
                f"VIN partiel sur l'assurance ({len(assurance.vin)} chars)",
                ValidationLevel.BLOCKING, "vin",
                correction_action="Fournir une attestation d'assurance avec le VIN complet"
            )

        return result


# ─── Validators VO ────────────────────────────────────────────────────────────

from engine.models.documents import ExtractedCGBarree


class CGBarreeValidator(BaseValidator):
    """
    Valide la carte grise barrée (V-33, V-34).

    Règles :
    - Barre diagonale détectée (V-33)
    - Mention "vendu le" + date + heure présentes
    - Nb signatures ↔ nb co-titulaires (V-34)
    """

    def validate(self, cg: ExtractedCGBarree) -> ValidationResult:
        result = ValidationResult(valid=True)

        # V-33 : barre diagonale
        if not cg.barre_diagonale:
            result.add_error(
                "CG_NON_BARREE",
                "La carte grise n'est pas barrée en diagonale",
                ValidationLevel.BLOCKING, "barre_diagonale",
                correction_action="Le vendeur doit barrer la CG en diagonale, noter 'vendu le', la date, l'heure et signer"
            )

        # Date + heure obligatoires
        if not cg.date_vente:
            result.add_error(
                "CG_BARREE_DATE_MISSING",
                "Date de vente absente sur la CG barrée",
                ValidationLevel.BLOCKING, "date_vente",
            )

        if not cg.heure_vente:
            result.add_error(
                "CG_BARREE_HEURE_MISSING",
                "Heure de vente absente sur la CG barrée (obligatoire)",
                ValidationLevel.BLOCKING, "heure_vente",
                correction_action="L'heure est obligatoire sur la CG barrée"
            )

        # V-34 : signatures — nb signatures ≥ nb co-titulaires
        nb_required = max(1, cg.co_titulaires_count)
        if cg.signatures_count < nb_required:
            result.add_error(
                "CG_BARREE_SIGNATURE_MISSING",
                f"Signatures insuffisantes : {cg.signatures_count} détectée(s), {nb_required} requise(s) "
                f"({cg.co_titulaires_count} co-titulaire(s))",
                ValidationLevel.BLOCKING, "signatures_count",
                correction_action="Tous les co-titulaires doivent signer la CG barrée"
            )

        # Numéro de formule
        if not cg.n_formule:
            result.add_error(
                "CG_BARREE_N_FORMULE_MISSING",
                "Numéro de formule absent sur la CG barrée",
                ValidationLevel.WARNING, "n_formule",
            )

        return result


class AttestationIdentiteProValidator(BaseValidator):
    """
    Vérifie que l'attestation de vérification d'identité pro est présente (V-38, D-31).

    Le pro doit avoir coché + signé électroniquement dans le portail
    qu'il a vérifié physiquement l'identité du client (NIV.1).
    Sans cette attestation, le dossier est bloqué.
    """

    def validate(self, attestation_presente: bool, attestation_datee: bool = True) -> ValidationResult:
        result = ValidationResult(valid=True)
        if not attestation_presente:
            result.add_error(
                "ATTESTATION_PRO_MISSING",
                "Attestation de vérification d'identité pro absente (D-31) — OBLIGATION LÉGALE convention SIV",
                ValidationLevel.BLOCKING, "attestation_identite_pro",
                correction_action="Le professionnel doit cocher l'attestation dans le portail (NIV.1 obligatoire)"
            )
        elif not attestation_datee:
            result.add_error(
                "ATTESTATION_PRO_NOT_DATED",
                "Attestation pro non datée",
                ValidationLevel.BLOCKING, "attestation_identite_pro",
            )
        return result


class CerfaValidator(BaseValidator):
    """
    Valide un formulaire Cerfa de demande de CG (V-23, V-34).

    Règles :
    - Signé (V-34)
    - Pas de rature (V-23)
    - Champs obligatoires présents
    """

    def validate(self, cerfa: "ExtractedCerfa") -> ValidationResult:
        from engine.models.documents import ExtractedCerfa
        result = ValidationResult(valid=True)

        if cerfa.rature_detectee:
            result.add_error(
                "CERFA_RATURE",
                "Rature détectée sur le Cerfa — document refusé",
                ValidationLevel.BLOCKING, "rature",
                correction_action="Fournir un nouveau Cerfa sans rature"
            )

        # Note : le client ne signe PAS les Cerfa 13749/13750.
        # Le pro signe comme vendeur professionnel — le cachet/signature pro
        # est apposé automatiquement après génération du PDF.
        # La seule signature client requise est sur la cession 15776 (VO uniquement).
        if not cerfa.signe_pro:
            result.add_error(
                "CERFA_NON_SIGNE_PRO",
                "Cachet/signature pro absent sur le Cerfa — sera apposé automatiquement à la génération",
                ValidationLevel.WARNING, "signe_pro",
                correction_action="Le système apposera le cachet/signature du pro automatiquement"
            )

        if not cerfa.nom_titulaire:
            result.add_error(
                "CERFA_NOM_MISSING", "Nom du titulaire absent sur le Cerfa",
                ValidationLevel.BLOCKING, "nom_titulaire",
            )

        if not cerfa.vin and not cerfa.immatriculation:
            result.add_error(
                "CERFA_VIN_MISSING", "VIN et immatriculation absents sur le Cerfa",
                ValidationLevel.BLOCKING, "vin",
            )

        return result
