"""Schémas Pydantic pour les endpoints dossiers."""
from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel

from engine.models.dossier import DossierType, DossierStatus


class DossierCreateRequest(BaseModel):
    type: DossierType
    professionnel_id: UUID
    vin: str | None = None
    immatriculation: str | None = None
    client_nom: str | None = None
    client_prenom: str | None = None
    client_email: str | None = None
    client_telephone: str | None = None


class DossierResponse(BaseModel):
    id: UUID
    reference: str
    type: str
    status: str
    diagnostic: str | None = None
    score: float | None = None
    vin: str | None = None
    immatriculation: str | None = None
    client_nom: str | None = None
    tax_estimate: dict[str, Any] | None = None
    created_at: datetime
    updated_at: datetime


class DossierDetailResponse(DossierResponse):
    blocking_rules: list[str] | None = None
    validation_errors: list[dict] | None = None
    validation_warnings: list[dict] | None = None
    cross_check_results: list[dict] | None = None
    documents: list[dict] | None = None
