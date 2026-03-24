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

        effet_result = DocumentDateValidator().validate("assurance_effet", assurance.date_effet, reference_date)
        result.errors.extend(effet_result.errors)
        if effet_result.is_blocking:
            result.valid = False

        echeance_result = DocumentDateValidator().validate("assurance_echeance", assurance.date_echeance, reference_date)
        result.errors.extend(echeance_result.errors)
        if echeance_result.is_blocking:
            result.valid = False

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
