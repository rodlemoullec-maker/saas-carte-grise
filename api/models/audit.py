"""
Modèle AuditLog — traçabilité de toutes les actions sur un dossier.

Obligatoire pour conformité SIV + RGPD. En version locale, ces logs
restent sur la machine de l'agent (jamais transmis à l'éditeur).
"""
from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import JSON, DateTime, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from api.models.base import Base


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), index=True)

    # Qui
    actor_type: Mapped[str] = mapped_column(String(20))  # SYSTEM | AGENT | API
    actor_id: Mapped[str | None] = mapped_column(String(36), nullable=True)

    # Quoi
    action: Mapped[str] = mapped_column(String(50), index=True)  # DOSSIER_CREATED, DOC_UPLOADED, PIPELINE_RUN, etc.
    resource_type: Mapped[str] = mapped_column(String(30))  # dossier | document | decision
    resource_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)

    # Détail
    detail: Mapped[str | None] = mapped_column(Text, nullable=True)
    extra_data: Mapped[dict | None] = mapped_column("metadata", JSON, nullable=True)
