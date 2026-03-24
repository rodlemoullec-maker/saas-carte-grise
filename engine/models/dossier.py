"""
Modèle de données principal : Dossier.

Un Dossier représente une demande de carte grise complète,
de la collecte des documents jusqu'à la soumission SIV.

TODO: compléter les champs selon l'évolution des cas métier.
"""
from __future__ import annotations

import uuid
from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class DossierType(str, Enum):
    NEUF_PRO_PARTICULIER = "NEUF_PRO_PARTICULIER"
    OCCASION_PRO_PARTICULIER = "OCCASION_PRO_PARTICULIER"
    OCCASION_PART_PARTICULIER = "OCCASION_PART_PARTICULIER"
    CHANGEMENT_ADRESSE = "CHANGEMENT_ADRESSE"
    DUPLICATA = "DUPLICATA"
    CHANGEMENT_TITULAIRE = "CHANGEMENT_TITULAIRE"


class DossierStatus(str, Enum):
    PENDING = "PENDING"           # Créé, en attente documents
    PROCESSING = "PROCESSING"     # Pipeline en cours
    REVUE_AGENT = "REVUE_AGENT"   # En attente validation agent
    CORRECTION = "CORRECTION"     # Retourné pour corrections
    ACCEPTE = "ACCEPTE"           # Validé, prêt SIV
    REJET = "REJET"               # Rejeté définitivement
    FRAUDE = "FRAUDE"             # Suspicion fraude — bloqué
    SUBMITTED = "SUBMITTED"       # Soumis au SIV
    CLOSED = "CLOSED"             # Finalisé


class Dossier(BaseModel):
    id: uuid.UUID = Field(default_factory=uuid.uuid4)
    type: DossierType
    status: DossierStatus = DossierStatus.PENDING
    score: float | None = None

    professionnel_id: uuid.UUID
    agent_id: uuid.UUID | None = None

    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    submitted_at: datetime | None = None

    blocking_rules_triggered: list[str] = Field(default_factory=list)
    issues: list[dict[str, Any]] = Field(default_factory=list)
    cross_check_results: list[dict[str, Any]] = Field(default_factory=list)

    # SIV
    siv_payload: dict[str, Any] | None = None
    siv_response: dict[str, Any] | None = None
    siv_reference: str | None = None

    class Config:
        use_enum_values = True
