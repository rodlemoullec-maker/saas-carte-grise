"""
Validateur SIRET.

Règles :
- 14 chiffres exactement
- Algorithme de Luhn (clé de contrôle)
- Vérification activité via API INSEE Sirene (dans integrations/)

Note : la validation INSEE est async et se fait dans le pipeline,
pas dans ce validateur synchrone.
"""
from __future__ import annotations

from engine.validators.base import BaseValidator, ValidationLevel, ValidationResult


class SIRETValidator(BaseValidator):

    def validate(self, siret: str) -> ValidationResult:
        result = ValidationResult(valid=True)
        siret = siret.replace(" ", "").replace("-", "")

        if not siret.isdigit():
            result.add_error(
                code="SIRET_NOT_NUMERIC",
                message="Le SIRET ne doit contenir que des chiffres",
                level=ValidationLevel.BLOCKING,
                field="siret",
                value=siret,
            )
            return result

        if len(siret) != 14:
            result.add_error(
                code="SIRET_LENGTH_INVALID",
                message=f"Le SIRET doit contenir 14 chiffres (reçu : {len(siret)})",
                level=ValidationLevel.BLOCKING,
                field="siret",
                value=siret,
                correction_action="Vérifier le SIRET sur le Kbis ou l'en-tête de la facture"
            )
            return result

        if not self._luhn_check(siret):
            result.add_error(
                code="SIRET_LUHN_INVALID",
                message="Le SIRET ne passe pas la vérification algorithmique (Luhn)",
                level=ValidationLevel.BLOCKING,
                field="siret",
                value=siret,
                correction_action="Vérifier le SIRET — probable erreur de saisie ou OCR"
            )

        return result

    def _luhn_check(self, siret: str) -> bool:
        total = 0
        for i, digit in enumerate(siret):
            n = int(digit)
            if i % 2 == 0:
                n *= 2
                if n > 9:
                    n -= 9
            total += n
        return total % 10 == 0
