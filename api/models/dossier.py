"""
Modèle Dossier — une demande de carte grise en cours de traitement.

Version locale : tous les champs liés au paiement par dossier, à la collecte
client à distance (lien SMS), et à la source de création (PRO/CLIENT) ont été
supprimés. Le dossier est créé localement par l'agent via le drag & drop d'emails.
"""
from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import JSON, Boolean, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from api.models.base import Base, TimestampMixin


class DossierDB(Base, TimestampMixin):
    __tablename__ = "dossiers"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    reference: Mapped[str] = mapped_column(String(20), unique=True, index=True)  # CG-2026-00001

    # Type et statut
    type: Mapped[str | None] = mapped_column(String(40), nullable=True)  # Déduit auto (VN/VO) après upload docs
    status: Mapped[str] = mapped_column(String(20), default="PENDING", index=True)

    # Véhicule
    vin: Mapped[str | None] = mapped_column(String(17), nullable=True, index=True)
    immatriculation: Mapped[str | None] = mapped_column(String(10), nullable=True, index=True)

    # Client final (acheteur) — données saisies/extraites par l'agent en local
    client_nom: Mapped[str | None] = mapped_column(String(255), nullable=True)
    client_prenom: Mapped[str | None] = mapped_column(String(255), nullable=True)
    client_email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    client_telephone: Mapped[str | None] = mapped_column(String(20), nullable=True)

    # Professionnel (l'agent — toujours le même en local, mais on garde la relation)
    professionnel_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("professionnels.id"), index=True,
    )

    # Métadonnées du dossier (consentement RGPD client, choix CPI, etc.)
    metadata_: Mapped[dict | None] = mapped_column("metadata", JSON, nullable=True)

    # Phase 1 — Diagnostic tri-couleur (VERT / ORANGE / ROUGE)
    diagnostic: Mapped[str | None] = mapped_column(String(10), nullable=True)
    blocages: Mapped[dict | None] = mapped_column(JSON, nullable=True)   # Liste V-XX déclenchés
    cross_check_results: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    validation_errors: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    validation_warnings: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    # Estimation des taxes (Y1, Y3-Y6)
    tax_estimate: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    # Préparation pour soumission SIV (l'agent soumet lui-même)
    siv_payload: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    submitted_at: Mapped[datetime | None] = mapped_column(nullable=True)
    siv_reference: Mapped[str | None] = mapped_column(String(50), nullable=True)
    cerfa_generated: Mapped[bool] = mapped_column(Boolean, default=False)

    # Contexte acheteur
    is_personne_morale: Mapped[bool] = mapped_column(Boolean, default=False)
    is_mineur: Mapped[bool] = mapped_column(Boolean, default=False)
    is_etranger: Mapped[bool] = mapped_column(Boolean, default=False)

    # Notes libres de l'agent
    agent_notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Relations
    professionnel = relationship("Professionnel", back_populates="dossiers")
    documents = relationship("DocumentDB", back_populates="dossier", lazy="selectin")
