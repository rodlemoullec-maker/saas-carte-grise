"""
Modèle Dossier — une demande de carte grise en cours de traitement.
"""
from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Float, ForeignKey, String, Text, Boolean
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from api.models.base import Base, TimestampMixin


class DossierDB(Base, TimestampMixin):
    __tablename__ = "dossiers"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    reference: Mapped[str] = mapped_column(String(20), unique=True, index=True)  # CG-2026-00001

    # Type et statut
    type: Mapped[str] = mapped_column(String(40))  # NEUF_PRO_PARTICULIER | OCCASION_PRO_PARTICULIER
    status: Mapped[str] = mapped_column(String(20), default="PENDING", index=True)

    # Véhicule
    vin: Mapped[str | None] = mapped_column(String(17), nullable=True, index=True)
    immatriculation: Mapped[str | None] = mapped_column(String(10), nullable=True, index=True)

    # Client final (acheteur)
    client_nom: Mapped[str | None] = mapped_column(String(255), nullable=True)
    client_prenom: Mapped[str | None] = mapped_column(String(255), nullable=True)
    client_email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    client_telephone: Mapped[str | None] = mapped_column(String(20), nullable=True)

    # Professionnel
    professionnel_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("professionnels.id"), index=True,
    )

    # Phase 1 — Diagnostic (VERT / ORANGE / ROUGE — pas de score)
    diagnostic: Mapped[str | None] = mapped_column(String(10), nullable=True)
    blocages: Mapped[dict | None] = mapped_column(JSONB, nullable=True)   # Liste V-XX declenches
    cross_check_results: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    validation_errors: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    validation_warnings: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    # Taxes estimation
    tax_estimate: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    # Phase 2 — Soumission
    submitted_at: Mapped[datetime | None] = mapped_column(nullable=True)
    siv_reference: Mapped[str | None] = mapped_column(String(50), nullable=True)
    siv_payload: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    siv_response: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    cpi_generated: Mapped[bool] = mapped_column(Boolean, default=False)

    # Contexte acheteur
    is_personne_morale: Mapped[bool] = mapped_column(Boolean, default=False)
    is_mineur: Mapped[bool] = mapped_column(Boolean, default=False)
    is_etranger: Mapped[bool] = mapped_column(Boolean, default=False)

    # Paiement honoraires (argent du porteur de projet)
    payment_preauth_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    payment_captured: Mapped[bool] = mapped_column(Boolean, default=False)
    montant_honoraires: Mapped[float | None] = mapped_column(Float, nullable=True)

    # Paiement taxes SIV (argent de l'Etat — mecanisme a confirmer apres reponse ANTS)
    tax_payment_method: Mapped[str | None] = mapped_column(String(30), nullable=True)
    tax_payment_status: Mapped[str | None] = mapped_column(String(20), nullable=True)

    # Relances
    relance_nb: Mapped[int] = mapped_column(default=0)
    relance_derniere: Mapped[datetime | None] = mapped_column(nullable=True)
    relance_prochaine: Mapped[datetime | None] = mapped_column(nullable=True)
    relance_escalade: Mapped[bool] = mapped_column(Boolean, default=False)

    # Agent override
    agent_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    agent_decision: Mapped[str | None] = mapped_column(String(20), nullable=True)
    agent_notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Relations
    professionnel = relationship("Professionnel", back_populates="dossiers")
    documents = relationship("DocumentDB", back_populates="dossier", lazy="selectin")
