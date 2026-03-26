"""
Router dossiers — CRUD complet + lancement pipeline.

POST   /dossiers/                Créer un nouveau dossier
GET    /dossiers/                Lister les dossiers (filtres, pagination)
GET    /dossiers/{id}            Détail d'un dossier
POST   /dossiers/{id}/go         Lancer le traitement (GO/NO-GO)
DELETE /dossiers/{id}            Annuler un dossier
"""
from __future__ import annotations

from datetime import datetime
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.models.base import get_db
from api.models.dossier import DossierDB
from api.schemas.dossier import DossierCreateRequest, DossierResponse

router = APIRouter()


def _generate_reference() -> str:
    """Génère une référence lisible : CG-2026-XXXXX."""
    import random
    year = datetime.utcnow().year
    seq = random.randint(10000, 99999)
    return f"CG-{year}-{seq}"


@router.post("/", response_model=DossierResponse, status_code=201)
async def create_dossier(
    request: DossierCreateRequest,
    db: AsyncSession = Depends(get_db),
):
    """Crée un nouveau dossier. Le statut initial est PENDING."""
    dossier = DossierDB(
        id=uuid4(),
        reference=_generate_reference(),
        type=request.type.value,
        status="PENDING",
        professionnel_id=request.professionnel_id,
        vin=request.vin,
        immatriculation=request.immatriculation,
        client_nom=request.client_nom,
        client_prenom=request.client_prenom,
        client_email=request.client_email,
        client_telephone=request.client_telephone,
    )
    db.add(dossier)
    await db.flush()
    return _to_response(dossier)


@router.get("/", response_model=list[DossierResponse])
async def list_dossiers(
    professionnel_id: UUID | None = None,
    status: str | None = None,
    limit: int = Query(default=50, le=200),
    offset: int = Query(default=0, ge=0),
    db: AsyncSession = Depends(get_db),
):
    """Liste les dossiers avec filtres et pagination."""
    query = select(DossierDB).order_by(DossierDB.created_at.desc())

    if professionnel_id:
        query = query.where(DossierDB.professionnel_id == professionnel_id)
    if status:
        query = query.where(DossierDB.status == status)

    query = query.offset(offset).limit(limit)
    result = await db.execute(query)
    dossiers = result.scalars().all()
    return [_to_response(d) for d in dossiers]


@router.get("/{dossier_id}", response_model=DossierResponse)
async def get_dossier(
    dossier_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """Retourne le détail complet d'un dossier."""
    dossier = await db.get(DossierDB, dossier_id)
    if not dossier:
        raise HTTPException(status_code=404, detail="Dossier non trouvé")
    return _to_response(dossier)


@router.post("/{dossier_id}/go")
async def go_dossier(
    dossier_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """
    Lance le traitement Phase 2 (GO/NO-GO).

    Pré-requis : diagnostic VERT ou ORANGE (pas ROUGE).
    Déclenche la pré-autorisation CB + passage en PROCESSING.
    """
    dossier = await db.get(DossierDB, dossier_id)
    if not dossier:
        raise HTTPException(status_code=404, detail="Dossier non trouvé")

    if dossier.diagnostic == "ROUGE":
        raise HTTPException(
            status_code=422,
            detail="Diagnostic ROUGE — corrections requises avant de lancer le traitement",
        )

    if dossier.status not in ("PENDING", "CORRECTION"):
        raise HTTPException(
            status_code=422,
            detail=f"Le dossier est en statut {dossier.status} — GO impossible",
        )

    # TODO: déclencher pré-autorisation CB (Stripe)
    # TODO: lancer task Celery Phase 2
    dossier.status = "PROCESSING"
    await db.flush()

    return {"status": "ok", "message": "Traitement lancé", "dossier_id": str(dossier_id)}


@router.get("/{dossier_id}/siv-payload")
async def get_siv_payload(
    dossier_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """
    Retourne les donnees formatees pour le formulaire SIV.

    Ce payload sert a :
    - L'extension navigateur (pre-remplissage automatique des champs SIV)
    - Le recapitulatif copier-coller (fallback si extension KO)
    - La livraison dossier SaaS (donnees structurees pour le pro)

    Les champs sont dans l'ordre du formulaire web SIV.
    """
    dossier = await db.get(DossierDB, dossier_id)
    if not dossier:
        raise HTTPException(status_code=404, detail="Dossier non trouve")

    if dossier.status not in ("ACCEPTE", "PROCESSING", "SUBMITTED"):
        raise HTTPException(
            status_code=422,
            detail=f"SIV payload non disponible — dossier en statut {dossier.status}",
        )

    # Construire le payload SIV depuis les donnees extraites
    # TODO: enrichir avec les champs reels du formulaire SIV (apres habilitation)
    payload = {
        "operation": "premiere_immatriculation" if "NEUF" in dossier.type else "changement_titulaire",
        "demandeur": {
            "nom": dossier.client_nom or "",
            "prenom": dossier.client_prenom or "",
            "is_personne_morale": dossier.is_personne_morale,
        },
        "vehicule": {
            "vin": dossier.vin or "",
            "immatriculation": dossier.immatriculation or "",
        },
        "taxes_estimees": dossier.tax_estimate,
        "diagnostic": dossier.diagnostic,
        "score": dossier.score,
        "_meta": {
            "dossier_id": str(dossier.id),
            "reference": dossier.reference,
            "generated_at": datetime.utcnow().isoformat(),
            "note": "Payload SIV — structure exacte a finaliser apres acces au formulaire SIV reel",
        },
    }

    return payload


@router.delete("/{dossier_id}")
async def cancel_dossier(
    dossier_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """Annule un dossier (soft delete — passage en CLOSED)."""
    dossier = await db.get(DossierDB, dossier_id)
    if not dossier:
        raise HTTPException(status_code=404, detail="Dossier non trouvé")

    if dossier.status in ("SUBMITTED", "CLOSED"):
        raise HTTPException(status_code=422, detail="Dossier déjà finalisé — annulation impossible")

    dossier.status = "CLOSED"
    await db.flush()
    return {"status": "ok", "message": "Dossier annulé"}


def _to_response(d: DossierDB) -> DossierResponse:
    return DossierResponse(
        id=d.id,
        reference=d.reference,
        type=d.type,
        status=d.status,
        diagnostic=d.diagnostic,
        score=d.score,
        vin=d.vin,
        immatriculation=d.immatriculation,
        client_nom=d.client_nom,
        tax_estimate=d.tax_estimate,
        created_at=d.created_at,
        updated_at=d.updated_at,
    )
