"""Schemas Pydantic pour les endpoints dossiers (version locale)."""
from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel


class DossierCreateRequest(BaseModel):
    """Création d'un dossier en local — saisie minimale par l'agent."""
    client_nom: str | None = None
    client_prenom: str | None = None
    client_email: str | None = None
    client_telephone: str | None = None
    notes: str | None = None


class DossierResponse(BaseModel):
    id: str
    reference: str
    type: str | None = None
    status: str
    diagnostic: str | None = None
    vin: str | None = None
    immatriculation: str | None = None
    client_nom: str | None = None
    client_prenom: str | None = None
    tax_estimate: dict[str, Any] | None = None
    created_at: datetime
    updated_at: datetime


class DossierDetailResponse(DossierResponse):
    blocages: list[dict] | None = None
    warnings: list[dict] | None = None
    cross_check_results: list[dict] | None = None
    documents: list[dict] | None = None
