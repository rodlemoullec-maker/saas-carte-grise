"""
Gestionnaire de licence locale — état d'activation côté agent.

Stocke et lit la licence sur le disque local de l'agent. Gère également
le mode essai gratuit (30 jours sans clé requise).

Fichiers gérés :
    {storage_path}/.license/license.key       → token de licence chiffré (Fernet)
    {storage_path}/.license/trial_started.json → marqueur de début d'essai

Aucun appel cloud n'est effectué — la vérification est 100% locale grâce
à la signature Ed25519.
"""
from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional

from engine.license.signer import (
    LicenseError,
    LicenseExpired,
    LicensePayload,
    verify_license,
)

logger = logging.getLogger(__name__)


# ─── Configuration ──────────────────────────────────────────────────────────

# Durée du mode essai en jours
TRIAL_DURATION_DAYS = 30

# Nombre max de dossiers utilisables en mode essai
TRIAL_MAX_DOSSIERS = 10


# ─── Modèle d'état ──────────────────────────────────────────────────────────


@dataclass
class LicenseStatus:
    """État de la licence sur cette installation."""
    is_valid: bool                  # True si l'agent peut utiliser le logiciel
    mode: str                       # "licensed" | "trial" | "expired" | "none"
    payload: LicensePayload | None  # Contenu de la licence si présente
    trial_started_at: str | None    # Date de début d'essai (ISO)
    trial_days_remaining: int | None
    trial_dossiers_used: int        # Nombre de dossiers consommés en essai
    message: str                    # Message à afficher à l'agent

    def to_dict(self) -> dict:
        return {
            "is_valid": self.is_valid,
            "mode": self.mode,
            "payload": self.payload.to_dict() if self.payload else None,
            "trial_started_at": self.trial_started_at,
            "trial_days_remaining": self.trial_days_remaining,
            "trial_dossiers_used": self.trial_dossiers_used,
            "message": self.message,
        }


# ─── Manager principal ─────────────────────────────────────────────────────


class LicenseManager:
    """
    Gère le cycle de vie de la licence sur une installation locale.

    Une seule instance par installation. Persistance dans data/.license/.
    """

    def __init__(self, base_path: str | Path = "./data") -> None:
        self.base_path = Path(base_path)
        self.license_dir = self.base_path / ".license"
        self.license_dir.mkdir(parents=True, exist_ok=True)

        self.license_file = self.license_dir / "license.key"
        self.trial_file = self.license_dir / "trial_started.json"

    # ─── Activation ────────────────────────────────────────────────────────

    def activate(self, token: str) -> LicensePayload:
        """
        Active une licence avec le token fourni par l'éditeur.

        Vérifie la signature et l'expiration avant de stocker.

        Args:
            token: la clé de licence reçue par email

        Raises:
            LicenseError (et sous-classes) si invalide
        """
        # Vérification cryptographique
        payload = verify_license(token.strip())

        # Stocker localement (en clair — la signature suffit à empêcher
        # la falsification, et le fichier est sur la machine de l'agent)
        self.license_file.write_text(token.strip(), encoding="utf-8")
        try:
            import os
            os.chmod(self.license_file, 0o600)
        except OSError:
            pass

        logger.info(
            f"[License] Activée pour {payload.agent_email} "
            f"(type={payload.type}, expires={payload.expires_at})"
        )
        return payload

    def deactivate(self) -> None:
        """Supprime la licence locale (l'agent retombe en mode essai si encore éligible)."""
        if self.license_file.exists():
            self.license_file.unlink()
            logger.info("[License] Désactivée")

    # ─── Lecture / vérification ────────────────────────────────────────────

    def get_status(self, dossiers_used_count: int = 0) -> LicenseStatus:
        """
        Retourne l'état actuel de la licence sur cette installation.

        Cette méthode est appelée :
        - Au démarrage du logiciel (pour décider si on bloque l'accès)
        - À chaque création de dossier (pour vérifier les quotas en mode essai)
        - Périodiquement par l'interface (pour afficher l'état dans l'UI)

        Args:
            dossiers_used_count: nombre de dossiers déjà créés en mode essai
        """
        # 1. Existe-t-il une licence stockée ?
        if self.license_file.exists():
            try:
                token = self.license_file.read_text(encoding="utf-8").strip()
                payload = verify_license(token)
                return LicenseStatus(
                    is_valid=True,
                    mode="licensed",
                    payload=payload,
                    trial_started_at=None,
                    trial_days_remaining=None,
                    trial_dossiers_used=0,
                    message=self._licensed_message(payload),
                )
            except LicenseExpired as e:
                # Licence expirée → on vérifie si l'essai est encore dispo
                logger.warning(f"[License] {e}")
                trial = self._get_or_start_trial()
                return self._build_trial_or_expired_status(trial, dossiers_used_count, expired=True)
            except LicenseError as e:
                logger.warning(f"[License] Licence stockée invalide : {e}")
                # Fichier corrompu → on le supprime et on retombe en essai
                try:
                    self.license_file.unlink()
                except OSError:
                    pass

        # 2. Pas de licence valide → mode essai
        trial = self._get_or_start_trial()
        return self._build_trial_or_expired_status(trial, dossiers_used_count, expired=False)

    # ─── Mode essai ────────────────────────────────────────────────────────

    def _get_or_start_trial(self) -> dict:
        """Lit ou démarre le marqueur d'essai."""
        if self.trial_file.exists():
            try:
                return json.loads(self.trial_file.read_text(encoding="utf-8"))
            except Exception:
                pass

        # Premier démarrage : on enregistre la date de début
        started_at = datetime.now(timezone.utc).isoformat()
        data = {"started_at": started_at}
        self.trial_file.write_text(json.dumps(data), encoding="utf-8")
        try:
            import os
            os.chmod(self.trial_file, 0o600)
        except OSError:
            pass
        logger.info(f"[License] Mode essai démarré le {started_at}")
        return data

    def _build_trial_or_expired_status(
        self,
        trial: dict,
        dossiers_used: int,
        expired: bool,
    ) -> LicenseStatus:
        """Construit le LicenseStatus en mode essai (ou licence expirée)."""
        try:
            started = datetime.fromisoformat(trial["started_at"])
            if started.tzinfo is None:
                started = started.replace(tzinfo=timezone.utc)
        except Exception:
            started = datetime.now(timezone.utc)

        elapsed = datetime.now(timezone.utc) - started
        days_remaining = max(0, TRIAL_DURATION_DAYS - elapsed.days)
        dossiers_remaining = max(0, TRIAL_MAX_DOSSIERS - dossiers_used)

        is_valid = days_remaining > 0 and dossiers_remaining > 0

        if expired:
            # La licence active a expiré, l'essai est aussi terminé
            mode = "expired"
            if is_valid:
                mode = "trial"  # essai encore disponible après expiration de la licence
            else:
                mode = "expired"
        else:
            mode = "trial" if is_valid else "expired"

        if mode == "trial":
            message = (
                f"Mode essai gratuit — il vous reste {days_remaining} jour(s) "
                f"et {dossiers_remaining} dossier(s)."
            )
        else:
            message = (
                "Votre période d'essai gratuit est terminée. "
                "Pour continuer à utiliser AutoDoc Pro, activez une licence."
            )

        return LicenseStatus(
            is_valid=is_valid,
            mode=mode,
            payload=None,
            trial_started_at=trial.get("started_at"),
            trial_days_remaining=days_remaining,
            trial_dossiers_used=dossiers_used,
            message=message,
        )

    def _licensed_message(self, payload: LicensePayload) -> str:
        """Message affiché quand l'agent a une licence valide."""
        if payload.type == "perpetual":
            return f"Licence perpétuelle active pour {payload.agent_name or payload.agent_email}."
        days = payload.days_remaining
        if days is None:
            return f"Licence active pour {payload.agent_name or payload.agent_email}."
        if days <= 30:
            return (
                f"Licence active pour {payload.agent_name or payload.agent_email}. "
                f"Elle expire dans {days} jour(s) — pensez à la renouveler."
            )
        return (
            f"Licence active pour {payload.agent_name or payload.agent_email} "
            f"({days} jours restants)."
        )


# ─── Singleton ──────────────────────────────────────────────────────────────


_manager: LicenseManager | None = None


def get_license_manager() -> LicenseManager:
    """Retourne l'instance unique du LicenseManager pour cette installation."""
    global _manager
    if _manager is None:
        from config.settings import get_settings
        settings = get_settings()
        # Le base_path correspond au dossier parent de storage_path
        # (par défaut ./data, contenant ./data/documents et ./data/.license)
        base = Path(settings.storage_path).parent
        _manager = LicenseManager(base)
    return _manager
