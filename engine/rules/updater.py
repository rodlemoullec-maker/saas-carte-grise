"""
Updater du bundle de règles — récupère la dernière version depuis l'éditeur.

Architecture :
- L'éditeur publie un fichier signé sur licenses.autodocpro.fr/rules/latest
- Le format attendu côté serveur :
    {
        "bundle": { version, description, released_at, ... },
        "signature": "base64url..."
    }
- L'updater télécharge ce fichier (HTTP GET, 1 fois par jour par défaut)
- Vérifie la signature Ed25519 avec la clé publique embarquée
- Compare la version avec celle actuellement installée
- Si plus récente : remplace data/rules/current.json et recharge le loader

Aucun envoi de données personnelles à l'éditeur — seule une requête HTTP
GET anonyme est effectuée pour récupérer le fichier de règles.
"""
from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from engine.rules.loader import (
    get_current_bundle,
    reload as reload_bundle,
    save_local_bundle,
    _get_local_bundle_path,
)

logger = logging.getLogger(__name__)


# ─── Modèle de résultat ────────────────────────────────────────────────────


@dataclass
class UpdateResult:
    """Résultat d'une tentative de mise à jour des règles."""
    status: str  # "updated" | "up_to_date" | "skipped" | "error"
    current_version: str
    new_version: str | None
    message: str

    def to_dict(self) -> dict:
        return {
            "status": self.status,
            "current_version": self.current_version,
            "new_version": self.new_version,
            "message": self.message,
        }


# ─── Fichier marqueur de dernière vérification ─────────────────────────────


def _last_check_path() -> Path:
    """Chemin du fichier qui mémorise la date de dernière vérification."""
    from config.settings import get_settings
    settings = get_settings()
    base = Path(settings.storage_path).parent
    return base / "rules" / ".last_check.json"


def _read_last_check() -> datetime | None:
    """Date de la dernière vérification réussie."""
    path = _last_check_path()
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return datetime.fromisoformat(data["last_check"])
    except Exception:
        return None


def _write_last_check() -> None:
    """Marque la date de la vérification courante."""
    path = _last_check_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps({"last_check": datetime.now(timezone.utc).isoformat()}),
        encoding="utf-8",
    )


def _should_check_now(interval_hours: int) -> bool:
    """Détermine si une vérification est due."""
    last = _read_last_check()
    if last is None:
        return True
    if last.tzinfo is None:
        last = last.replace(tzinfo=timezone.utc)
    elapsed = (datetime.now(timezone.utc) - last).total_seconds() / 3600
    return elapsed >= interval_hours


# ─── Téléchargement et application ─────────────────────────────────────────


async def check_for_updates(force: bool = False) -> UpdateResult:
    """
    Vérifie si une nouvelle version du bundle est disponible.

    Args:
        force: si True, force la vérification même si l'intervalle n'est pas écoulé

    Returns:
        UpdateResult avec status, version actuelle, version disponible, message
    """
    from config.settings import get_settings
    settings = get_settings()

    current = get_current_bundle()
    current_version = current.version

    if not force and not _should_check_now(settings.rules_check_interval_hours):
        return UpdateResult(
            status="skipped",
            current_version=current_version,
            new_version=None,
            message="Vérification ignorée — intervalle non écoulé.",
        )

    try:
        import httpx
    except ImportError as e:
        return UpdateResult(
            status="error",
            current_version=current_version,
            new_version=None,
            message=f"httpx requis pour la vérification : {e}",
        )

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(settings.rules_update_url)
            response.raise_for_status()
            payload = response.json()
    except Exception as e:
        logger.warning(f"[rules updater] échec téléchargement : {e}")
        return UpdateResult(
            status="error",
            current_version=current_version,
            new_version=None,
            message=f"Impossible de contacter le serveur de l'éditeur : {e}",
        )

    if not isinstance(payload, dict) or "bundle" not in payload or "signature" not in payload:
        return UpdateResult(
            status="error",
            current_version=current_version,
            new_version=None,
            message="Format de réponse invalide (champs 'bundle' et 'signature' attendus).",
        )

    bundle_data = payload["bundle"]
    signature = payload["signature"]
    new_version = bundle_data.get("version", "unknown")

    # Marquer la vérification comme effectuée même si pas d'update
    _write_last_check()

    if new_version == current_version:
        return UpdateResult(
            status="up_to_date",
            current_version=current_version,
            new_version=new_version,
            message="Vous avez déjà la dernière version des règles.",
        )

    # Sauvegarder le nouveau bundle (avec vérification de signature)
    try:
        save_local_bundle(bundle_data, signature)
    except Exception as e:
        return UpdateResult(
            status="error",
            current_version=current_version,
            new_version=new_version,
            message=f"Échec de l'écriture du nouveau bundle : {e}",
        )

    # Recharger le loader pour appliquer immédiatement
    reload_bundle()

    logger.info(
        f"[rules updater] Mise à jour appliquée : {current_version} → {new_version}"
    )

    return UpdateResult(
        status="updated",
        current_version=current_version,
        new_version=new_version,
        message=(
            f"Règles mises à jour : version {new_version}. "
            f"Les nouveaux contrôles sont actifs immédiatement."
        ),
    )


def get_update_status() -> dict:
    """État courant des règles : version, source, date de dernière vérification."""
    bundle = get_current_bundle()
    last = _read_last_check()
    return {
        "version": bundle.version,
        "description": bundle.description,
        "released_at": bundle.released_at,
        "source": bundle.source,
        "last_check": last.isoformat() if last else None,
    }
