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
    """
    Vérifie la cohérence âge ↔ catégorie de permis (règle C-16).

    < 14 ans : aucun véhicule autorisé
    14-15 ans : AM uniquement (cyclo ≤ 50cc)
    16-17 ans : AM + A1 (125cc / 11kW)
    ≥ 18 ans  : A2 + B (voiture, moto ≤ 35kW)
    ≥ 20 ans (avec 2 ans A2) : A
    """

    # Catégories autorisées par tranche d'âge
    CATEGORIES_BY_AGE: dict[tuple[int, int], set[str]] = {
        (14, 15): {"AM"},
        (16, 17): {"AM", "A1"},
        (18, 19): {"AM", "A1", "A2", "B"},
        (20, 999): {"AM", "A1", "A2", "A", "B", "BE", "C", "CE", "D"},
    }

    def validate(self, date_naissance: date, permis_categories: list[str] | None = None,
                 reference_date: date | None = None) -> ValidationResult:
        result = ValidationResult(valid=True)
        ref = reference_date or date.today()
        age = (ref - date_naissance).days // 365

        if age < 14:
            result.add_error(
                code="BUYER_TOO_YOUNG",
                message=f"L'acheteur a {age} ans — aucun véhicule motorisé autorisé",
                level=ValidationLevel.BLOCKING, field="date_naissance",
            )
            return result

        if age < 18:
            allowed = set()
            for (min_age, max_age), cats in self.CATEGORIES_BY_AGE.items():
                if min_age <= age <= max_age:
                    allowed = cats
                    break
            if permis_categories:
                held = set(permis_categories)
                forbidden = held - allowed
                if forbidden:
                    result.add_error(
                        code="AGE_CATEGORY_MISMATCH",
                        message=(
                            f"L'acheteur a {age} ans — catégorie(s) {forbidden} non autorisée(s). "
                            f"Autorisé : {allowed}"
                        ),
                        level=ValidationLevel.BLOCKING, field="categories_permis",
                        correction_action="Vérifier l'âge et les catégories de permis"
                    )
            result.add_error(
                code="BUYER_UNDERAGE_ESCALADE",
                message=f"L'acheteur est mineur ({age} ans) — escalade obligatoire",
                level=ValidationLevel.WARNING, field="date_naissance",
                correction_action="Dossier mineur : autorisation parentale (D-27) + livret famille (D-26) requis"
            )
        return result


class CTDateValidator(BaseValidator):
    """
    Vérifie la validité du contrôle technique pour une vente (règles V-16, V-17).

    Règle : CT < 6 mois à la DATE DE SAISIE SIV (pas à la date de commande).
    5-6 mois → WARNING (risque expiration avant saisie).
    Contre-visite : < 2 mois.
    """

    def validate(self, date_ct: date, saisie_siv_date: date | None = None) -> ValidationResult:
        result = ValidationResult(valid=True)
        ref = saisie_siv_date or date.today()
        age_days = (ref - date_ct).days

        if age_days > 183:  # > 6 mois
            result.add_error(
                code="CT_TOO_OLD",
                message=f"Contrôle technique trop ancien ({age_days} jours — max 183 jours à la saisie SIV)",
                level=ValidationLevel.BLOCKING, field="date_ct",
                correction_action="Un nouveau contrôle technique est requis avant la saisie SIV"
            )
        elif age_days > 152:  # 5-6 mois → WARNING
            result.add_error(
                code="CT_EXPIRING_SOON",
                message=f"Contrôle technique proche de l'expiration ({age_days} jours — expire dans {183 - age_days} jours)",
                level=ValidationLevel.WARNING, field="date_ct",
                correction_action="Vérifier que la saisie SIV pourra être effectuée avant expiration"
            )
        return result

    def validate_contre_visite(self, date_cv: date, reference_date: date | None = None) -> ValidationResult:
        result = ValidationResult(valid=True)
        ref = reference_date or date.today()
        age_days = (ref - date_cv).days
        if age_days > 61:  # > 2 mois
            result.add_error(
                code="CONTRE_VISITE_EXPIRED",
                message=f"Contre-visite expirée ({age_days} jours — max 61 jours)",
                level=ValidationLevel.BLOCKING, field="date_contre_visite",
                correction_action="Repasser un contrôle technique complet"
            )
        return result


class TitreSejourValidator(BaseValidator):
    """
    Vérifie la validité du titre de séjour (V-13).

    - Expiré → BLOCKING
    - Récépissé de renouvellement → WARNING (accepté mais risqué)
    - Expire dans < 30 jours → WARNING
    """

    def validate(self, date_expiration: date, is_recepisse: bool = False,
                 reference_date: date | None = None) -> ValidationResult:
        result = ValidationResult(valid=True)
        ref = reference_date or date.today()

        if is_recepisse:
            result.add_error(
                code="TITRE_SEJOUR_RECEPISSE",
                message="Récépissé de renouvellement de titre de séjour — accepté mais risqué",
                level=ValidationLevel.WARNING, field="titre_sejour",
                correction_action="Préférer le titre de séjour définitif. Vérifier la durée du récépissé (3-6 mois)."
            )

        if date_expiration < ref:
            delta = (ref - date_expiration).days
            result.add_error(
                code="TITRE_SEJOUR_EXPIRED",
                message=f"Titre de séjour expiré depuis {delta} jour(s)",
                level=ValidationLevel.BLOCKING, field="date_expiration",
                correction_action="Fournir un titre de séjour valide ou un récépissé de renouvellement"
            )
        elif (date_expiration - ref).days < 30:
            result.add_error(
                code="TITRE_SEJOUR_EXPIRING",
                message=f"Titre de séjour expire dans {(date_expiration - ref).days} jour(s)",
                level=ValidationLevel.WARNING, field="date_expiration",
                correction_action="Anticiper le renouvellement — risque d'expiration avant saisie SIV"
            )

        return result


class KbisValidator(BaseValidator):
    """
    Vérifie la fraîcheur du Kbis / avis SIRENE (V-15).

    Règle : Kbis < 3 mois (92 jours) à la date de la demande.
    """

    def validate(self, date_kbis: date, reference_date: date | None = None) -> ValidationResult:
        result = ValidationResult(valid=True)
        ref = reference_date or date.today()
        age_days = (ref - date_kbis).days

        if age_days > 92:
            result.add_error(
                code="KBIS_TOO_OLD",
                message=f"Kbis trop ancien ({age_days} jours — max 92 jours / 3 mois)",
                level=ValidationLevel.BLOCKING, field="date_kbis",
                correction_action="Fournir un Kbis de moins de 3 mois (téléchargeable sur infogreffe.fr)"
            )
        elif age_days > 75:
            result.add_error(
                code="KBIS_EXPIRING_SOON",
                message=f"Kbis proche de l'expiration ({age_days} jours — expire dans {92 - age_days} jours)",
                level=ValidationLevel.WARNING, field="date_kbis",
            )

        return result


class CodeCessionValidator(BaseValidator):
    """
    Vérifie la validité du code de cession ANTS (règle V-18).

    5 caractères. Validité : 15 jours.
    Ignoré si le pro est habilité SIV direct.
    """

    def validate(self, date_generation: date, pro_habilite_siv: bool = False,
                 reference_date: date | None = None) -> ValidationResult:
        result = ValidationResult(valid=True)
        if pro_habilite_siv:
            return result  # Pro habilité SIV : code cession non requis

        ref = reference_date or date.today()
        age_days = (ref - date_generation).days

        if age_days > 15:
            result.add_error(
                code="CODE_CESSION_EXPIRED",
                message=f"Code de cession ANTS expiré ({age_days} jours — max 15 jours)",
                level=ValidationLevel.BLOCKING, field="code_cession",
                correction_action="Le vendeur doit générer un nouveau code de cession sur ANTS"
            )
        return result
