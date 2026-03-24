"""
Validateur de dates et délais de validité des documents.
"""
from __future__ import annotations

from datetime import date, timedelta

from engine.validators.base import BaseValidator, ValidationLevel, ValidationResult

# Délais de validité en jours par type de justificatif de domicile
DOMICILE_VALIDITY_DAYS: dict[str, int] = {
    "facture_electricite": 92,
    "facture_gaz": 92,
    "facture_eau": 92,
    "facture_telephone": 92,
    "facture_internet": 92,
    "quittance_loyer": 92,
    "releve_bancaire": 92,
    "avis_imposition": 365,
    "attestation_hebergement": -1,  # -1 = pas de délai
}


class DocumentDateValidator(BaseValidator):
    """Vérifie la validité temporelle d'un document (expiration, fraîcheur)."""

    def validate(self, doc_type: str, doc_date: date, reference_date: date | None = None) -> ValidationResult:
        result = ValidationResult(valid=True)
        ref = reference_date or date.today()

        if doc_type == "identite":
            return self._validate_identite(doc_date, ref, result)
        elif doc_type == "permis":
            return self._validate_permis(doc_date, ref, result)
        elif doc_type == "assurance_effet":
            return self._validate_assurance_effet(doc_date, ref, result)
        elif doc_type == "assurance_echeance":
            return self._validate_assurance_echeance(doc_date, ref, result)
        elif doc_type in DOMICILE_VALIDITY_DAYS:
            return self._validate_domicile(doc_type, doc_date, ref, result)
        else:
            result.add_error(
                code="UNKNOWN_DOC_TYPE",
                message=f"Type de document inconnu pour validation date : {doc_type}",
                level=ValidationLevel.WARNING,
            )
        return result

    def _validate_identite(self, expiration: date, ref: date, result: ValidationResult) -> ValidationResult:
        if expiration < ref:
            delta = (ref - expiration).days
            if delta > 5 * 365:
                result.add_error(
                    code="IDENTITY_DOC_EXPIRED",
                    message=f"Pièce d'identité expirée depuis {delta} jours (> 5 ans)",
                    level=ValidationLevel.BLOCKING,
                    field="date_expiration",
                    correction_action="Fournir une pièce d'identité en cours de validité"
                )
            else:
                result.add_error(
                    code="IDENTITY_DOC_EXPIRED_WITHIN_5Y",
                    message=f"Pièce d'identité expirée depuis {delta} jours (≤ 5 ans — acceptée pour ressortissants français uniquement)",
                    level=ValidationLevel.WARNING,
                    field="date_expiration",
                    correction_action="Vérifier la nationalité — si non français, document refusé"
                )
        return result

    def _validate_permis(self, expiration: date, ref: date, result: ValidationResult) -> ValidationResult:
        if expiration < ref:
            result.add_error(
                code="DRIVING_LICENSE_EXPIRED",
                message="Permis de conduire expiré",
                level=ValidationLevel.BLOCKING,
                field="date_validite",
                correction_action="Fournir un permis valide ou un récépissé de renouvellement"
            )
        return result

    def _validate_assurance_effet(self, date_effet: date, ref: date, result: ValidationResult) -> ValidationResult:
        if date_effet > ref:
            delta = (date_effet - ref).days
            result.add_error(
                code="INSURANCE_NOT_YET_ACTIVE",
                message=f"L'assurance ne prend effet que dans {delta} jour(s)",
                level=ValidationLevel.BLOCKING,
                field="date_effet",
                correction_action="L'assurance doit être active à la date de la demande"
            )
        return result

    def _validate_assurance_echeance(self, date_echeance: date, ref: date, result: ValidationResult) -> ValidationResult:
        if date_echeance < ref:
            result.add_error(
                code="INSURANCE_EXPIRED",
                message="L'assurance est expirée",
                level=ValidationLevel.BLOCKING,
                field="date_echeance",
                correction_action="Fournir une attestation d'assurance en cours de validité"
            )
        return result

    def _validate_domicile(self, doc_type: str, doc_date: date, ref: date, result: ValidationResult) -> ValidationResult:
        max_days = DOMICILE_VALIDITY_DAYS.get(doc_type, 92)
        if max_days == -1:
            return result  # Pas de délai (attestation hébergement)

        age_days = (ref - doc_date).days
        if age_days > max_days:
            result.add_error(
                code="DOMICILE_TOO_OLD",
                message=f"Justificatif de domicile trop ancien ({age_days} jours, max {max_days})",
                level=ValidationLevel.BLOCKING,
                field="date_document",
                correction_action=f"Fournir un justificatif de domicile datant de moins de {max_days} jours"
            )
        return result


class AgeValidator(BaseValidator):
    """Vérifie que l'acheteur est majeur (≥ 18 ans)."""

    def validate(self, date_naissance: date, reference_date: date | None = None) -> ValidationResult:
        result = ValidationResult(valid=True)
        ref = reference_date or date.today()
        age = (ref - date_naissance).days // 365

        if age < 18:
            result.add_error(
                code="BUYER_UNDERAGE",
                message=f"L'acheteur est mineur ({age} ans) — immatriculation impossible",
                level=ValidationLevel.BLOCKING,
                field="date_naissance",
            )
        return result
