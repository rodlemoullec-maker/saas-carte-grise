"""Schémas Pydantic pour les endpoints dossiers."""
from __future__ import annotations
from datetime import datetime
from uuid import UUID
from pydantic import BaseModel
from engine.models.dossier import DossierType, DossierStatus

class DossierCreateRequest(BaseModel):
    type: DossierType
    professionnel_id: UUID

class DossierResponse(BaseModel):
    id: UUID
    type: DossierType
    status: DossierStatus
    score: float | None
    created_at: datetime
    updated_at: datetime
