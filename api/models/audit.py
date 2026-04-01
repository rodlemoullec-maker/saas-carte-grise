"""
Modèle AuditLog — traçabilité de toutes les actions sur un dossier.

Obligatoire pour conformité SIV + RGPD.
"""
from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from api.models.base import Base


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), index=True)

    # Qui
    actor_type: Mapped[str] = mapped_column(String(20))  # SYSTEM | PRO | AGENT | API
    actor_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)

    # Quoi
    action: Mapped[str] = mapped_column(String(50), index=True)  # DOSSIER_CREATED, DOC_UPLOADED, PIPELINE_RUN, etc.
    resource_type: Mapped[str] = mapped_column(String(30))  # dossier | document | decision
    resource_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True, index=True)

    # Détail
    detail: Mapped[str | None] = mapped_column(Text, nullable=True)
    extra_data: Mapped[dict | None] = mapped_column("metadata", JSONB, nullable=True)

    # IP / user-agent (pour les actions API)
    ip_address: Mapped[str | None] = mapped_column(String(45), nullable=True)
    user_agent: Mapped[str | None] = mapped_column(String(500), nullable=True)
