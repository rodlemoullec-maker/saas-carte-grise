"""
Modèle Professionnel — le client B2B (garage, concessionnaire, revendeur).
"""
from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Boolean, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from api.models.base import Base, TimestampMixin


class Professionnel(Base, TimestampMixin):
    __tablename__ = "professionnels"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    raison_sociale: Mapped[str] = mapped_column(String(255))
    siret: Mapped[str | None] = mapped_column(String(14), nullable=True, index=True)
    siren: Mapped[str | None] = mapped_column(String(9), nullable=True, index=True)
    email: Mapped[str] = mapped_column(String(255), unique=True)
    password_hash: Mapped[str | None] = mapped_column(String(255), nullable=True)
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

    # Paramétrage profil (rempli à l'installation)
    nom_commerce: Mapped[str | None] = mapped_column(String(255), nullable=True)
    telephone_commerce: Mapped[str | None] = mapped_column(String(20), nullable=True)
    email_commerce: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # Documents profil (chemins S3)
    cachet_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
    signature_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
    kbis_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
    kbis_extracted: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    # Assurance flotte
    assurance_flotte_vn: Mapped[bool] = mapped_column(Boolean, default=False)
    assurance_flotte_vo: Mapped[bool] = mapped_column(Boolean, default=False)
    # Si pas de flotte : demander attestation au client automatiquement ?
    demander_assurance_client_vn: Mapped[bool] = mapped_column(Boolean, default=False)
    demander_assurance_client_vo: Mapped[bool] = mapped_column(Boolean, default=False)

    # Relances
    relance_mode: Mapped[str] = mapped_column(
        String(20), default="PRO"
    )

    # Setup complet ?
    setup_complete: Mapped[bool] = mapped_column(Boolean, default=False)

    # Type de compte : détermine le flux du système
    # VENDEUR_HABILITE = vend un véhicule, soumet lui-même au SIV (défaut)
    # VENDEUR_NON_HABILITE = vend un véhicule, son agent habilité soumet au SIV
    # AGENT_HABILITE = ne vend pas, fait la CG pour le compte du client
    type_compte: Mapped[str] = mapped_column(String(30), default="VENDEUR_HABILITE")

    # Infos agent habilité (pour VENDEUR_NON_HABILITE uniquement)
    agent_nom: Mapped[str | None] = mapped_column(String(255), nullable=True)
    agent_siret: Mapped[str | None] = mapped_column(String(14), nullable=True)
    agent_numero_habilitation: Mapped[str | None] = mapped_column(String(50), nullable=True)
    agent_telephone: Mapped[str | None] = mapped_column(String(20), nullable=True)
    agent_email: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # Page publique (URL permanente)
    slug: Mapped[str | None] = mapped_column(String(100), nullable=True, unique=True, index=True)
    page_publique_active: Mapped[bool] = mapped_column(Boolean, default=False)

    # CGV acceptées
    cgv_acceptees: Mapped[bool] = mapped_column(Boolean, default=False)

    # Actif
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    # Relations
    dossiers = relationship("DossierDB", back_populates="professionnel", lazy="selectin")
