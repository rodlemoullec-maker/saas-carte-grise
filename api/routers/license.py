"""
Router licence — activation et vérification locale.

GET   /license/status     État actuel de la licence (valide / essai / expirée)
POST  /license/activate   Active une licence avec un token
POST  /license/deactivate Désactive la licence (retombe en essai si éligible)

Aucune communication avec un serveur cloud — la vérification est 100% locale
grâce à la signature Ed25519 de l'éditeur embarquée dans le code.
"""
from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from api.models.base import get_db
from api.models.dossier import DossierDB
from engine.license.manager import get_license_manager
from engine.license.signer import (
    LicenseError,
    LicenseExpired,
    LicenseFormatError,
    LicenseInvalidSignature,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/license", tags=["license"])


# ─── Schémas ────────────────────────────────────────────────────────────────


class ActivateRequest(BaseModel):
    token: str


# ─── Helpers ────────────────────────────────────────────────────────────────


async def _count_dossiers(db: AsyncSession) -> int:
    """Compte le nombre total de dossiers créés sur cette installation."""
    result = await db.execute(select(func.count()).select_from(DossierDB))
    return int(result.scalar() or 0)


# ─── Endpoints ──────────────────────────────────────────────────────────────


@router.get("/status")
async def get_license_status(db: AsyncSession = Depends(get_db)):
    """
    Retourne l'état actuel de la licence sur cette installation.

    Appelé au démarrage de l'interface pour décider si on bloque l'accès,
    et périodiquement pour rafraîchir l'affichage du statut dans l'UI.
    """
    manager = get_license_manager()
    dossiers_count = await _count_dossiers(db)
    status = manager.get_status(dossiers_used_count=dossiers_count)
    return status.to_dict()


@router.post("/activate")
async def activate_license(req: ActivateRequest):
    """
    Active une licence avec le token fourni par l'éditeur.

    Le token est vérifié cryptographiquement (signature Ed25519 + expiration).
    En cas de succès, il est stocké localement (~/.autodoc-pro/license.key).
    """
    if not req.token or len(req.token.strip()) < 20:
        raise HTTPException(422, "Token de licence vide ou invalide")

    manager = get_license_manager()
    try:
        payload = manager.activate(req.token)
    except LicenseInvalidSignature as e:
        raise HTTPException(403, detail={
            "error": "license_invalid_signature",
            "message": (
                "Cette licence ne provient pas d'AutoDoc Pro. "
                "Vérifiez que vous avez bien copié l'intégralité du token "
                "fourni dans votre email d'achat."
            ),
        }) from e
    except LicenseExpired as e:
        raise HTTPException(403, detail={
            "error": "license_expired",
            "message": str(e),
        }) from e
    except LicenseFormatError as e:
        raise HTTPException(422, detail={
            "error": "license_format_invalid",
            "message": (
                "Le format du token est invalide. Copiez-le tel quel "
                "depuis votre email, sans ajouter d'espace ni de retour à la ligne."
            ),
        }) from e
    except LicenseError as e:
        raise HTTPException(500, detail={
            "error": "license_activation_failed",
            "message": str(e),
        }) from e

    return {
        "status": "ok",
        "message": f"Licence activée pour {payload.agent_name or payload.agent_email}.",
        "license": payload.to_dict(),
    }


@router.post("/deactivate")
async def deactivate_license():
    """
    Désactive la licence locale.

    L'agent retombe en mode essai si la période d'essai n'est pas terminée,
    sinon en mode "expired" et le logiciel devient inutilisable jusqu'à
    réactivation d'une licence valide.
    """
    manager = get_license_manager()
    manager.deactivate()
    return {"status": "ok", "message": "Licence désactivée."}
