"""
Router décisions — résultats Phase 1, overrides agent, retry.

GET    /decisions/{dossier_id}           Résultat diagnostic Phase 1
POST   /decisions/{dossier_id}/override  Agent override (REVUE_AGENT → ACCEPTE/REJET)
POST   /decisions/{dossier_id}/retry     Relancer le pipeline Phase 1
"""
from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from api.models.base import get_db
from api.models.dossier import DossierDB

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
        "score": dossier.score,
        "blocking_rules": dossier.blocking_rules,
        "validation_errors": dossier.validation_errors,
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
    await db.flush()

    # TODO: créer AuditLog entry
    # TODO: si ACCEPTE → mettre à jour diagnostic VERT
    # TODO: notifier le pro

    return {
        "status": "ok",
        "dossier_id": str(dossier_id),
        "new_status": request.decision,
        "agent_id": str(request.agent_id),
    }


@router.post("/{dossier_id}/retry")
async def retry_pipeline(
    dossier_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """
    Relance le pipeline Phase 1 après correction.

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

    dossier.status = "PROCESSING"
    dossier.diagnostic = None
    dossier.score = None
    dossier.blocking_rules = None
    dossier.validation_errors = None
    dossier.validation_warnings = None
    dossier.cross_check_results = None
    await db.flush()

    # TODO: lancer task Celery pipeline Phase 1
    # from workers.pipeline import process_dossier
    # process_dossier.delay(str(dossier_id))

    return {"status": "ok", "message": "Pipeline Phase 1 relancé", "dossier_id": str(dossier_id)}
