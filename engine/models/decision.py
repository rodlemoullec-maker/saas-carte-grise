"""
Modèles de données pour les décisions et résultats de validation.
"""
from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel


class DecisionStatus(str, Enum):
    ACCEPTE = "ACCEPTE"
    CORRECTION = "CORRECTION"
    REJET = "REJET"
    FRAUDE = "FRAUDE"
    REVUE_AGENT = "REVUE_AGENT"


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
    code: str                     # ex: "VIN_COC_FACTURE_MISMATCH"
    document_type: str | None = None
    field: str | None = None
    message: str                  # Message lisible
    correction_action: str | None = None  # Action corrective proposée


class CrossCheckResult(BaseModel):
    rule_name: str
    status: CrossCheckStatus
    source_a: str
    source_b: str
    field: str
    value_a: str | None = None
    value_b: str | None = None
    confidence: float = 1.0
    detail: str | None = None


class Decision(BaseModel):
    status: DecisionStatus
    score: float
    issues: list[Issue] = []
    cross_check_results: list[CrossCheckResult] = []
    blocking_rules_triggered: list[str] = []
    requires_human_review: bool = False
    fraud_indicators: list[str] = []
    metadata: dict[str, Any] = {}
