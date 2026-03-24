"""Schémas Pydantic pour les endpoints documents."""
from __future__ import annotations
from datetime import datetime
from typing import Any
from uuid import UUID
from pydantic import BaseModel
from engine.models.documents import DocumentType, DocumentStatus

class DocumentResponse(BaseModel):
    id: UUID
    dossier_id: UUID
    type: DocumentType
    status: DocumentStatus
    ocr_confidence: float | None
    extracted_data: dict[str, Any] | None
    uploaded_at: datetime
