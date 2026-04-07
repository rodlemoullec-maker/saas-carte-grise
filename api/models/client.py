"""
Modèle Client — base de clients récurrents de l'agent.

Beaucoup d'agents traitent plusieurs dossiers pour le même client final
(ex: un particulier qui change de véhicule, une société avec plusieurs
véhicules de fonction, etc.). Ce modèle permet à l'agent de retrouver
rapidement ses clients existants et leurs dossiers passés.

Stockage local SQLite — aucune donnée transmise à l'éditeur.
"""
from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import JSON, Boolean, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from api.models.base import Base, TimestampMixin


class ClientDB(Base, TimestampMixin):
    """
    Représente un client de l'agent (particulier ou personne morale).

    Un client peut avoir plusieurs dossiers au fil du temps. La relation
    Dossier → Client est faible (lien manuel par l'agent ou auto-rattachement
    par fuzzy match nom/email).
    """
    __tablename__ = "clients"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))

    # Type
    type: Mapped[str] = mapped_column(String(20), default="PHYSIQUE")  # PHYSIQUE | MORALE

    # Identité personne physique
    nom: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    prenom: Mapped[str | None] = mapped_column(String(255), nullable=True)
    date_naissance: Mapped[str | None] = mapped_column(String(20), nullable=True)
    lieu_naissance: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # Identité personne morale
    raison_sociale: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    siret: Mapped[str | None] = mapped_column(String(14), nullable=True, index=True)
    representant_legal: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # Coordonnées (communes aux deux types)
    email: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    telephone: Mapped[str | None] = mapped_column(String(20), nullable=True, index=True)

    # Adresse
    adresse: Mapped[str | None] = mapped_column(Text, nullable=True)
    code_postal: Mapped[str | None] = mapped_column(String(10), nullable=True)
    ville: Mapped[str | None] = mapped_column(String(255), nullable=True)
    pays: Mapped[str | None] = mapped_column(String(50), nullable=True, default="France")

    # Notes libres de l'agent
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Statistiques (mises à jour par l'agent ou par un cron interne)
    nb_dossiers: Mapped[int] = mapped_column(default=0)
    dernier_dossier_at: Mapped[datetime | None] = mapped_column(nullable=True)

    # Flags
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    # Métadonnées flexibles
    metadata_: Mapped[dict | None] = mapped_column("metadata", JSON, nullable=True)

    @property
    def display_name(self) -> str:
        """Nom d'affichage selon le type de client."""
        if self.type == "MORALE" and self.raison_sociale:
            return self.raison_sociale
        if self.nom:
            if self.prenom:
                return f"{self.prenom} {self.nom}"
            return self.nom
        return f"Client {self.id[:8]}"
