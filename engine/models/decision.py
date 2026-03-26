"""
Modeles de donnees pour les decisions et resultats de validation.
"""
from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel


class Diagnostic(str, Enum):
    """
    Diagnostic tri-couleur — logique binaire, pas de score.

    ROUGE  = au moins 1 verrouillage V-XX declenche (blocage)
    ORANGE = zero verrouillage mais au moins 1 warning
    VERT   = zero verrouillage, zero warning — pret pour GO/NO-GO
    """
    VERT = "VERT"
    ORANGE = "ORANGE"
    ROUGE = "ROUGE"


class DecisionStatus(str, Enum):
    ACCEPTE = "ACCEPTE"         # VERT → pret pour Phase 2
    CORRECTION = "CORRECTION"   # ROUGE → corrections requises
    FRAUDE = "FRAUDE"           # Fraude detectee → blocage + alerte
    REVUE_AGENT = "REVUE_AGENT" # ORANGE → le pro decide (ou escalade)


class IssueSeverity(str, Enum):
    BLOCKING = "BLOCKING"
    WARNING = "WARNING"
    INFO = "INFO"


class IssueCategory(str, Enum):
    VIN = "VIN"
    IDENTITY = "IDENTITY"
    VEHICLE = "VEHICLE"
    TEMPORAL = "TEMPORAL"
    DOCUMENT = "DOCUMENT"
    FRAUD = "FRAUD"


class CrossCheckStatus(str, Enum):
    PASS = "PASS"
    FAIL = "FAIL"
    WARNING = "WARNING"
    SKIPPED = "SKIPPED"


class Issue(BaseModel):
    severity: IssueSeverity
    category: IssueCategory
    code: str
    document_type: str | None = None
    field: str | None = None
    message: str
    correction_action: str | None = None


class CrossCheckResult(BaseModel):
    rule_name: str
    status: CrossCheckStatus
    source_a: str
    source_b: str
    field: str
    value_a: str | None = None
    value_b: str | None = None
    confidence: float = 1.0       # Score OCR du document source (pas un score dossier)
    detail: str | None = None


class Decision(BaseModel):
    """
    Resultat du moteur de decision.

    Pas de score pondere — un dossier est conforme ou il ne l'est pas.
    Le pro voit la liste des blocages et warnings, pas un chiffre abstrait.
    """
    diagnostic: Diagnostic
    status: DecisionStatus
    blocages: list[str] = []           # Liste des V-XX declenches (BLOCKING)
    warnings: list[str] = []           # Liste des warnings (non bloquants)
    cross_check_results: list[CrossCheckResult] = []
    fraud_indicators: list[str] = []
    requires_human_review: bool = False
    metadata: dict[str, Any] = {}
