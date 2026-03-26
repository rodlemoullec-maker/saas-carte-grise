"""
Modèle Professionnel — le client B2B (garage, concessionnaire, revendeur).
"""
from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Boolean, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from api.models.base import Base, TimestampMixin


class Professionnel(Base, TimestampMixin):
    __tablename__ = "professionnels"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    raison_sociale: Mapped[str] = mapped_column(String(255))
    siret: Mapped[str] = mapped_column(String(14), unique=True, index=True)
    siren: Mapped[str] = mapped_column(String(9), index=True)
    email: Mapped[str] = mapped_column(String(255), unique=True)
    telephone: Mapped[str | None] = mapped_column(String(20), nullable=True)

    # Adresse
    adresse: Mapped[str | None] = mapped_column(Text, nullable=True)
    code_postal: Mapped[str | None] = mapped_column(String(5), nullable=True)
    ville: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # Habilitation
    habilite_siv: Mapped[bool] = mapped_column(Boolean, default=False)
    agrement_tresor: Mapped[bool] = mapped_column(Boolean, default=False)
    numero_habilitation: Mapped[str | None] = mapped_column(String(50), nullable=True)

    # Service mode
    service_mode: Mapped[str] = mapped_column(
        String(20), default="FULL_SERVICE"  # FULL_SERVICE | SAAS
    )

    # Facturation
    mode_facturation: Mapped[str] = mapped_column(
        String(20), default="UNITAIRE"  # UNITAIRE | ABONNEMENT
    )
    stripe_customer_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    sepa_mandate_id: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # Relances
    relance_mode: Mapped[str] = mapped_column(
        String(20), default="PRO"  # PRO | SYSTEME (le pro relance ou le système relance le client)
    )

    # Actif
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    # Relations
    dossiers = relationship("DossierDB", back_populates="professionnel", lazy="selectin")
