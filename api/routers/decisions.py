"""
Router décisions — résultats Phase 1 et retry.

GET    /decisions/{dossier_id}        Résultat diagnostic Phase 1
POST   /decisions/{dossier_id}/retry  Relancer le pipeline Phase 1 après correction

Version locale : pas d'override agent (l'agent EST l'utilisateur unique,
il modifie directement le dossier).
"""
from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from api.models.base import get_db
from api.models.dossier import DossierDB

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/{dossier_id}")
async def get_decision(
    dossier_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Retourne le résultat du diagnostic Phase 1."""
    dossier = await db.get(DossierDB, dossier_id)
    if not dossier:
        raise HTTPException(status_code=404, detail="Dossier non trouvé")

    return {
        "dossier_id": dossier.id,
        "reference": dossier.reference,
        "status": dossier.status,
        "diagnostic": dossier.diagnostic,
        "blocages": dossier.blocages,
        "validation_warnings": dossier.validation_warnings,
        "cross_check_results": dossier.cross_check_results,
        "tax_estimate": dossier.tax_estimate,
        "agent_notes": dossier.agent_notes,
    }


@router.post("/{dossier_id}/retry")
async def retry_pipeline(
    dossier_id: str,
    db: AsyncSession = Depends(get_db),
):
    """
    Relance le diagnostic après correction.
    Le dossier doit être en CORRECTION ou PENDING.
    """
    dossier = await db.get(DossierDB, dossier_id)
    if not dossier:
        raise HTTPException(status_code=404, detail="Dossier non trouvé")

    if dossier.status not in ("CORRECTION", "PENDING", "DIAGNOSTIC"):
        raise HTTPException(
            status_code=422,
            detail=f"Retry impossible — le dossier est en statut {dossier.status}",
        )

    # Relancer le diagnostic en synchrone
    from api.routers.documents import _build_dossier_dict
    from engine.pipeline.realtime import run_diagnostic

    dossier_dict = await _build_dossier_dict(db, dossier)
    result = run_diagnostic(dossier_dict)

    dossier.diagnostic = result["diagnostic"]
    dossier.blocages = result.get("blocages")
    dossier.tax_estimate = result.get("tax_estimate")
    dossier.status = "DIAGNOSTIC"
    await db.flush()

    logger.info(f"[Decision] Retry dossier={dossier_id} → diagnostic={result['diagnostic']}")

    return {
        "status": "ok",
        "message": "Diagnostic relancé",
        "dossier_id": dossier_id,
        "diagnostic": result["diagnostic"],
    }
