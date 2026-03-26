"""
Moteur de relances automatiques.

Quand un dossier est en CORRECTION (docs manquants, invalides, qualite),
le systeme genere des relances selon la config du pro :
  - relance_mode = "PRO"     → email au pro qui relaie a son client
  - relance_mode = "SYSTEME" → email directement au client final

Frequence configurable : J+1, J+3, J+7 (defaut).
Escalade si pas de reponse apres N relances.

Architecture :
  - Les relances sont gerees comme des tasks Celery periodiques
  - Chaque dossier en CORRECTION a un "relance_state" en BDD
  - Le scheduler verifie quotidiennement les dossiers a relancer
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from enum import Enum
from typing import Any
from uuid import UUID

logger = logging.getLogger(__name__)


class RelanceMode(str, Enum):
    PRO = "PRO"           # Le pro relance son client
    SYSTEME = "SYSTEME"   # Le systeme relance directement le client


@dataclass
class RelanceConfig:
    """Configuration des relances pour un professionnel."""
    mode: RelanceMode = RelanceMode.PRO
    delais_jours: list[int] = field(default_factory=lambda: [1, 3, 7])  # J+1, J+3, J+7
    max_relances: int = 3
    escalade_apres: int = 3      # Escalade apres N relances sans reponse
    email_pro: str = ""
    email_client: str | None = None


@dataclass
class RelanceState:
    """Etat de relance d'un dossier."""
    dossier_id: UUID
    nb_relances_envoyees: int = 0
    derniere_relance: datetime | None = None
    prochaine_relance: datetime | None = None
    pieces_manquantes: list[str] = field(default_factory=list)
    corrections_requises: list[str] = field(default_factory=list)
    escalade: bool = False


@dataclass
class RelanceAction:
    """Action de relance a executer."""
    dossier_id: UUID
    destinataire: str            # Email
    template: str                # Template email
    context: dict[str, Any]      # Variables template
    relance_numero: int


class RelanceScheduler:
    """
    Moteur de relances.

    Usage (dans un Celery beat ou cron) :
        scheduler = RelanceScheduler()
        actions = scheduler.check_pending_relances(dossiers_en_correction)
        for action in actions:
            await send_email(action.destinataire, action.template, action.context)
            update_relance_state(action.dossier_id, ...)
    """

    def compute_relances(
        self,
        dossier_id: UUID,
        diagnostic_date: datetime,
        config: RelanceConfig,
        state: RelanceState,
        today: datetime | None = None,
    ) -> RelanceAction | None:
        """
        Determine si une relance doit etre envoyee aujourd'hui pour ce dossier.
        Retourne une RelanceAction si oui, None sinon.
        """
        now = today or datetime.utcnow()

        # Max relances atteint ?
        if state.nb_relances_envoyees >= config.max_relances:
            if not state.escalade:
                # Declencher l'escalade
                state.escalade = True
                return RelanceAction(
                    dossier_id=dossier_id,
                    destinataire=config.email_pro,  # Toujours au pro pour l'escalade
                    template="escalade_relance",
                    context={
                        "reference": str(dossier_id),
                        "nb_relances": state.nb_relances_envoyees,
                        "pieces_manquantes": "\n".join(f"- {p}" for p in state.pieces_manquantes),
                        "corrections_requises": "\n".join(f"- {c}" for c in state.corrections_requises),
                    },
                    relance_numero=state.nb_relances_envoyees + 1,
                )
            return None  # Escalade deja faite, plus rien a faire

        # Calculer la prochaine date de relance
        if state.nb_relances_envoyees < len(config.delais_jours):
            delai = config.delais_jours[state.nb_relances_envoyees]
        else:
            delai = config.delais_jours[-1]  # Repeter le dernier delai

        reference_date = state.derniere_relance or diagnostic_date
        prochaine = reference_date + timedelta(days=delai)

        if now < prochaine:
            return None  # Pas encore le moment

        # Determiner le destinataire
        if config.mode == RelanceMode.SYSTEME and config.email_client:
            destinataire = config.email_client
        else:
            destinataire = config.email_pro

        # Construire le contexte
        pieces_list = "\n".join(f"- {p}" for p in state.pieces_manquantes) if state.pieces_manquantes else ""
        corrections_list = "\n".join(f"- {c}" for c in state.corrections_requises) if state.corrections_requises else ""

        template = "documents_manquants" if state.pieces_manquantes else "correction_requise"

        return RelanceAction(
            dossier_id=dossier_id,
            destinataire=destinataire,
            template=template,
            context={
                "reference": str(dossier_id),
                "client_nom": "",  # A remplir par l'appelant
                "documents_list": pieces_list,
                "corrections_list": corrections_list,
                "relance_numero": state.nb_relances_envoyees + 1,
                "jours_depuis_diagnostic": (now - diagnostic_date).days,
            },
            relance_numero=state.nb_relances_envoyees + 1,
        )

    def build_relance_state_from_phase1(
        self,
        dossier_id: UUID,
        completeness_errors: list[dict],
        validation_errors: list[dict],
        quality_errors: list[dict],
    ) -> RelanceState:
        """
        Construit le RelanceState initial apres un diagnostic ROUGE.
        Extrait les pieces manquantes et corrections requises.
        """
        pieces = []
        corrections = []

        for err in completeness_errors:
            pieces.append(err.get("message", err.get("code", "Document manquant")))

        for err in quality_errors:
            corrections.append(err.get("message", err.get("code", "Qualite insuffisante")))

        for err in validation_errors:
            correction = err.get("correction", err.get("message", ""))
            if correction:
                corrections.append(correction)

        return RelanceState(
            dossier_id=dossier_id,
            pieces_manquantes=pieces,
            corrections_requises=corrections,
        )
