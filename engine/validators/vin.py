"""
Validateur VIN — ISO 3779.

Règles :
- 17 caractères exactement
- Caractères alphanumériques uniquement (I, O, Q interdits)
- Position 10 : code année modèle valide
- WMI (3 premiers chars) : vérifiable contre base constructeurs
- Check digit (position 9) : algorithme nord-américain (optionnel pour EU, utile détection fraude)
"""
from __future__ import annotations

from engine.validators.base import BaseValidator, ValidationLevel, ValidationResult

# Caractères interdits dans un VIN
VIN_FORBIDDEN_CHARS = frozenset("IOQ")

# Caractères autorisés
VIN_VALID_CHARS = frozenset("ABCDEFGHJKLMNPRSTUVWXYZ0123456789")

# Codes année modèle valides (position 10)
VIN_YEAR_CHARS = frozenset("ABCDEFGHJKLMNPRSTUVWXY123456789")

# Valeurs pour l'algorithme check digit
_TRANSLITERATION = {
    'A': 1, 'B': 2, 'C': 3, 'D': 4, 'E': 5, 'F': 6, 'G': 7, 'H': 8,
    'J': 1, 'K': 2, 'L': 3, 'M': 4, 'N': 5,         'P': 7, 'R': 9,
    'S': 2, 'T': 3, 'U': 4, 'V': 5, 'W': 6, 'X': 7, 'Y': 8, 'Z': 9,
    '0': 0, '1': 1, '2': 2, '3': 3, '4': 4, '5': 5, '6': 6, '7': 7, '8': 8, '9': 9,
}
_WEIGHTS = [8, 7, 6, 5, 4, 3, 2, 10, 0, 9, 8, 7, 6, 5, 4, 3, 2]


class VINValidator(BaseValidator):

    def validate(self, vin: str) -> ValidationResult:
        result = ValidationResult(valid=True)
        vin = vin.upper().replace(" ", "").replace("-", "")

        if len(vin) != 17:
            result.add_error(
                code="VIN_LENGTH_INVALID",
                message=f"Le VIN doit contenir exactement 17 caractères (reçu : {len(vin)})",
                level=ValidationLevel.BLOCKING,
                field="vin",
                value=vin,
                correction_action="Vérifier le VIN sur le COC et la facture"
            )
            return result

        for char in vin:
            if char in VIN_FORBIDDEN_CHARS:
                result.add_error(
                    code="VIN_FORBIDDEN_CHAR",
                    message=f"Caractère interdit '{char}' dans le VIN (I, O, Q sont exclus du standard VIN)",
                    level=ValidationLevel.BLOCKING,
                    field="vin",
                    value=vin,
                    correction_action="Vérifier la lecture OCR — probable confusion O/0 ou I/1"
                )
                return result

        for char in vin:
            if char not in VIN_VALID_CHARS:
                result.add_error(
                    code="VIN_INVALID_CHAR",
                    message=f"Caractère invalide '{char}' dans le VIN",
                    level=ValidationLevel.BLOCKING,
                    field="vin",
                    value=vin,
                )
                return result

        if vin[9] not in VIN_YEAR_CHARS:
            result.add_error(
                code="VIN_YEAR_CHAR_INVALID",
                message=f"Caractère d'année modèle invalide en position 10 : '{vin[9]}'",
                level=ValidationLevel.WARNING,
                field="vin",
                value=vin,
            )

        # Check digit (algorithme nord-américain — informatif pour véhicules EU)
        check_digit = self._compute_check_digit(vin)
        if check_digit is not None and vin[8] != check_digit:
            result.add_error(
                code="VIN_CHECK_DIGIT_MISMATCH",
                message="Check digit VIN incorrect — possible erreur de saisie ou falsification",
                level=ValidationLevel.WARNING,  # WARNING car non obligatoire pour véhicules EU
                field="vin",
                value=vin,
                correction_action="Vérifier le VIN directement sur le véhicule"
            )

        return result

    def _compute_check_digit(self, vin: str) -> str | None:
        """
        Calcule le check digit attendu (position 9).
        Retourne None si le calcul est impossible (caractères hors table).
        """
        try:
            total = sum(_TRANSLITERATION[c] * w for c, w in zip(vin, _WEIGHTS))
            remainder = total % 11
            return 'X' if remainder == 10 else str(remainder)
        except KeyError:
            return None
