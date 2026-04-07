"""
Modèle Agent — l'utilisateur unique du logiciel local AutoDoc Pro.

L'agent habilité SIV est seul utilisateur de l'instance locale.
Il est responsable de ses dossiers, de ses clients, et de la conformité.
Le concept de "vendeur partenaire" et de "sous-comptes" a été supprimé
lors de la migration vers le logiciel local.
"""
from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import JSON, Boolean, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from api.models.base import Base, TimestampMixin


class Professionnel(Base, TimestampMixin):
    """
    Représente l'agent habilité SIV qui utilise cette instance locale.
    En version locale, il y a généralement UN SEUL enregistrement
    correspondant à l'utilisateur du logiciel installé.
    """
    __tablename__ = "professionnels"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    raison_sociale: Mapped[str] = mapped_column(String(255))
    siret: Mapped[str | None] = mapped_column(String(14), nullable=True, index=True)
    siren: Mapped[str | None] = mapped_column(String(9), nullable=True, index=True)
    email: Mapped[str] = mapped_column(String(255), unique=True)
    telephone: Mapped[str | None] = mapped_column(String(20), nullable=True)

    # Adresse
    adresse: Mapped[str | None] = mapped_column(Text, nullable=True)
    code_postal: Mapped[str | None] = mapped_column(String(5), nullable=True)
    ville: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # Habilitation SIV (l'agent doit être habilité pour utiliser le logiciel)
    habilite_siv: Mapped[bool] = mapped_column(Boolean, default=True)
    numero_habilitation: Mapped[str | None] = mapped_column(String(50), nullable=True)

    # Identité commerciale (affichée dans les Cerfa et emails de relance)
    nom_commerce: Mapped[str | None] = mapped_column(String(255), nullable=True)
    telephone_commerce: Mapped[str | None] = mapped_column(String(20), nullable=True)
    email_commerce: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # Documents profil (chemins fichiers locaux chiffrés)
    cachet_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
    signature_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
    kbis_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
    kbis_extracted: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    # Setup complet ?
    setup_complete: Mapped[bool] = mapped_column(Boolean, default=False)

    # CGL (Conditions Générales de Licence) acceptées
    cgl_acceptees: Mapped[bool] = mapped_column(Boolean, default=False)

    # Actif (peut être désactivé si licence expirée)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    # Relations
    dossiers = relationship("DossierDB", back_populates="professionnel", lazy="selectin")
