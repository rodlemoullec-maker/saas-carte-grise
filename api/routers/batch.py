"""
Router batch — operations groupees sur les dossiers.

POST   /dossiers/batch           Creer plusieurs dossiers en lot
POST   /dossiers/batch/launch    Lancer le traitement sur une selection
GET    /dossiers/batch/status     Statut groupe d'un lot
"""
from __future__ import annotations

from datetime import datetime
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.models.base import get_db
from api.models.dossier import DossierDB

router = APIRouter()


class BatchDossierItem(BaseModel):
    type: str  # NEUF_PRO_PARTICULIER | OCCASION_PRO_PARTICULIER
    vin: str | None = None
    immatriculation: str | None = None
    client_nom: str | None = None
    client_prenom: str | None = None
    client_email: str | None = None


class BatchCreateRequest(BaseModel):
    professionnel_id: UUID
    dossiers: list[BatchDossierItem]


class BatchLaunchRequest(BaseModel):
    dossier_ids: list[UUID]


def _generate_reference() -> str:
    import random
    year = datetime.utcnow().year
    seq = random.randint(10000, 99999)
    return f"CG-{year}-{seq}"


@router.post("/batch", status_code=201)
async def create_batch(
    request: BatchCreateRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Cree plusieurs dossiers en un seul appel.
    Le pro uploade ensuite les documents pour chaque dossier.
    """
    if len(request.dossiers) > 50:
        raise HTTPException(status_code=422, detail="Maximum 50 dossiers par lot")

    created = []
    for item in request.dossiers:
        dossier = DossierDB(
            id=uuid4(),
            reference=_generate_reference(),
            type=item.type,
            status="PENDING",
            professionnel_id=request.professionnel_id,
            vin=item.vin,
            immatriculation=item.immatriculation,
            client_nom=item.client_nom,
            client_prenom=item.client_prenom,
            client_email=item.client_email,
        )
        db.add(dossier)
        created.append({
            "id": str(dossier.id),
            "reference": dossier.reference,
            "type": dossier.type,
            "client_nom": dossier.client_nom,
            "vin": dossier.vin,
            "immatriculation": dossier.immatriculation,
        })

    await db.flush()

    return {
        "count": len(created),
        "dossiers": created,
    }


@router.post("/batch/launch")
async def launch_batch(
    request: BatchLaunchRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Lance le traitement Phase 2 sur une selection de dossiers.

    Pre-requis : chaque dossier doit avoir un diagnostic VERT ou ORANGE.
    Pre-autorisation CB : montant = honoraires x nb dossiers lances.
    Debit uniquement sur les dossiers aboutis (CPI genere).
    """
    if len(request.dossier_ids) > 50:
        raise HTTPException(status_code=422, detail="Maximum 50 dossiers par lot")

    result = await db.execute(
        select(DossierDB).where(DossierDB.id.in_(request.dossier_ids))
    )
    dossiers = result.scalars().all()

    if len(dossiers) != len(request.dossier_ids):
        raise HTTPException(status_code=404, detail="Un ou plusieurs dossiers non trouves")

    launched = []
    blocked = []

    for d in dossiers:
        if d.diagnostic == "ROUGE":
            blocked.append({
                "id": str(d.id),
                "reference": d.reference,
                "reason": "Diagnostic ROUGE — corrections requises",
            })
        elif d.status not in ("PENDING", "CORRECTION"):
            blocked.append({
                "id": str(d.id),
                "reference": d.reference,
                "reason": f"Statut {d.status} — GO impossible",
            })
        else:
            d.status = "PROCESSING"
            launched.append({
                "id": str(d.id),
                "reference": d.reference,
            })

    await db.flush()

    # TODO: pre-autorisation CB groupee (montant = honoraires x nb launched)
    # TODO: lancer tasks Celery Phase 2 pour chaque dossier

    return {
        "launched": len(launched),
        "blocked": len(blocked),
        "dossiers_launched": launched,
        "dossiers_blocked": blocked,
    }


@router.get("/batch/status")
async def batch_status(
    professionnel_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """
    Retourne un tableau recapitulatif de tous les dossiers d'un pro
    avec leur diagnostic VERT/ORANGE/ROUGE.
    """
    result = await db.execute(
        select(DossierDB)
        .where(DossierDB.professionnel_id == professionnel_id)
        .order_by(DossierDB.created_at.desc())
    )
    dossiers = result.scalars().all()

    summary = {"VERT": 0, "ORANGE": 0, "ROUGE": 0, "PENDING": 0}
    items = []

    for d in dossiers:
        diag = d.diagnostic or "PENDING"
        summary[diag] = summary.get(diag, 0) + 1
        items.append({
            "id": str(d.id),
            "reference": d.reference,
            "type": d.type,
            "status": d.status,
            "diagnostic": d.diagnostic,
            "client_nom": d.client_nom,
            "vin": d.vin,
            "created_at": d.created_at.isoformat() if d.created_at else None,
        })

    return {
        "professionnel_id": str(professionnel_id),
        "total": len(items),
        "summary": summary,
        "dossiers": items,
    }
