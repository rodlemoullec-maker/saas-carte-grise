"""
Router décisions — résultats Phase 1, overrides agent, retry.

GET    /decisions/{dossier_id}           Résultat diagnostic Phase 1
POST   /decisions/{dossier_id}/override  Agent override (REVUE_AGENT → ACCEPTE/REJET)
POST   /decisions/{dossier_id}/retry     Relancer le pipeline Phase 1
"""
from __future__ import annotations

import logging
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from api.models.base import get_db
from api.models.dossier import DossierDB
from api.models.professionnel import Professionnel

logger = logging.getLogger(__name__)

router = APIRouter()


class AgentOverrideRequest(BaseModel):
    agent_id: UUID
    decision: str  # ACCEPTE | REJET
    notes: str | None = None


@router.get("/{dossier_id}")
async def get_decision(
    dossier_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """Retourne le résultat du diagnostic Phase 1."""
    dossier = await db.get(DossierDB, dossier_id)
    if not dossier:
        raise HTTPException(status_code=404, detail="Dossier non trouvé")

    return {
        "dossier_id": str(dossier.id),
        "reference": dossier.reference,
        "status": dossier.status,
        "diagnostic": dossier.diagnostic,
        "blocages": dossier.blocages,
        "validation_warnings": dossier.validation_warnings,
        "cross_check_results": dossier.cross_check_results,
        "tax_estimate": dossier.tax_estimate,
        "agent_decision": dossier.agent_decision,
        "agent_notes": dossier.agent_notes,
    }


@router.post("/{dossier_id}/override")
async def agent_override(
    dossier_id: UUID,
    request: AgentOverrideRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Override agent — permet de forcer ACCEPTE ou REJET sur un dossier
    en REVUE_AGENT. Loggé dans l'audit trail.
    """
    dossier = await db.get(DossierDB, dossier_id)
    if not dossier:
        raise HTTPException(status_code=404, detail="Dossier non trouvé")

    if dossier.status != "REVUE_AGENT":
        raise HTTPException(
            status_code=422,
            detail=f"Override impossible — le dossier est en statut {dossier.status} (attendu: REVUE_AGENT)",
        )

    if request.decision not in ("ACCEPTE", "REJET"):
        raise HTTPException(status_code=422, detail="Décision invalide — ACCEPTE ou REJET uniquement")

    dossier.status = request.decision
    dossier.agent_id = request.agent_id
    dossier.agent_decision = request.decision
    dossier.agent_notes = request.notes

    # Si accepté → diagnostic VERT
    if request.decision == "ACCEPTE":
        dossier.diagnostic = "VERT"

    await db.flush()

    # Notifier le pro
    pro = await db.get(Professionnel, dossier.professionnel_id)
    if pro and pro.email_commerce:
        from notifications.email import send_email
        template = "dossier_accepte" if request.decision == "ACCEPTE" else "dossier_rejete"
        await send_email(pro.email_commerce, template, {
            "reference": dossier.reference or "",
            "diagnostic": dossier.diagnostic or "",
            "tax_total": str(dossier.tax_estimate.get("total", "—")) if dossier.tax_estimate else "—",
            "motifs": request.notes or "Aucun motif précisé.",
        })

    logger.info(f"[Decision] Override dossier={dossier_id} → {request.decision} par agent={request.agent_id}")

    return {
        "status": "ok",
        "dossier_id": str(dossier_id),
        "new_status": request.decision,
        "diagnostic": dossier.diagnostic,
        "agent_id": str(request.agent_id),
    }


@router.post("/{dossier_id}/retry")
async def retry_pipeline(
    dossier_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """
    Relance le diagnostic après correction.
    Le dossier doit être en CORRECTION ou PENDING.
    """
    dossier = await db.get(DossierDB, dossier_id)
    if not dossier:
        raise HTTPException(status_code=404, detail="Dossier non trouvé")

    if dossier.status not in ("CORRECTION", "PENDING"):
        raise HTTPException(
            status_code=422,
            detail=f"Retry impossible — le dossier est en statut {dossier.status}",
        )

    # Relancer le diagnostic en synchrone (comme l'endpoint run-diagnostic)
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
        "dossier_id": str(dossier_id),
        "diagnostic": result["diagnostic"],
    }
