"""
Classes de base pour les validateurs.

Un validateur prend une donnée extraite et vérifie
sa conformité aux règles métier.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum


class ValidationLevel(str, Enum):
    BLOCKING = "BLOCKING"
    WARNING = "WARNING"
    INFO = "INFO"


@dataclass
class ValidationError:
    code: str
    message: str
    level: ValidationLevel
    field: str | None = None
    value: str | None = None
    correction_action: str | None = None


@dataclass
class ValidationResult:
    valid: bool
    errors: list[ValidationError] = field(default_factory=list)
    warnings: list[ValidationError] = field(default_factory=list)

    @property
    def is_blocking(self) -> bool:
        return any(e.level == ValidationLevel.BLOCKING for e in self.errors)

    def add_error(self, code: str, message: str, level: ValidationLevel,
                  field: str | None = None, value: str | None = None,
                  correction_action: str | None = None) -> None:
        error = ValidationError(code=code, message=message, level=level,
                                field=field, value=value, correction_action=correction_action)
        if level == ValidationLevel.WARNING:
            self.warnings.append(error)
        else:
            self.errors.append(error)
            if level == ValidationLevel.BLOCKING:
                self.valid = False


class BaseValidator(ABC):

    @abstractmethod
    def validate(self, *args, **kwargs) -> ValidationResult:
        ...
