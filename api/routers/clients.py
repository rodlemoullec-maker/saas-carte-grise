"""
Router clients — base de clients récurrents de l'agent.

GET    /clients              Liste (filtre optionnel ?q=)
POST   /clients              Créer
GET    /clients/{id}         Détail
PUT    /clients/{id}         Mettre à jour
DELETE /clients/{id}         Supprimer (soft : is_active=False)
GET    /clients/{id}/dossiers   Dossiers rattachés
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from api.models.base import get_db
from api.models.client import ClientDB
from api.models.dossier import DossierDB

router = APIRouter(prefix="/clients", tags=["clients"])


class ClientRequest(BaseModel):
    type: str = "PHYSIQUE"  # PHYSIQUE | MORALE
    nom: str | None = None
    prenom: str | None = None
    date_naissance: str | None = None
    lieu_naissance: str | None = None
    raison_sociale: str | None = None
    siret: str | None = None
    representant_legal: str | None = None
    email: str | None = None
    telephone: str | None = None
    adresse: str | None = None
    code_postal: str | None = None
    ville: str | None = None
    pays: str | None = "France"
    notes: str | None = None


def _to_dict(c: ClientDB) -> dict:
    return {
        "id": c.id,
        "type": c.type,
        "display_name": c.display_name,
        "nom": c.nom,
        "prenom": c.prenom,
        "date_naissance": c.date_naissance,
        "lieu_naissance": c.lieu_naissance,
        "raison_sociale": c.raison_sociale,
        "siret": c.siret,
        "representant_legal": c.representant_legal,
        "email": c.email,
        "telephone": c.telephone,
        "adresse": c.adresse,
        "code_postal": c.code_postal,
        "ville": c.ville,
        "pays": c.pays,
        "notes": c.notes,
        "nb_dossiers": c.nb_dossiers,
        "dernier_dossier_at": c.dernier_dossier_at.isoformat() if c.dernier_dossier_at else None,
        "is_active": c.is_active,
        "created_at": c.created_at.isoformat() if c.created_at else None,
        "updated_at": c.updated_at.isoformat() if c.updated_at else None,
    }


@router.get("")
async def list_clients(q: str | None = None, db: AsyncSession = Depends(get_db)):
    stmt = select(ClientDB).where(ClientDB.is_active == True)  # noqa: E712
    if q:
        like = f"%{q}%"
        stmt = stmt.where(
            or_(
                ClientDB.nom.ilike(like),
                ClientDB.prenom.ilike(like),
                ClientDB.raison_sociale.ilike(like),
                ClientDB.siret.ilike(like),
                ClientDB.email.ilike(like),
                ClientDB.telephone.ilike(like),
            )
        )
    stmt = stmt.order_by(ClientDB.updated_at.desc())
    result = await db.execute(stmt)
    return {"clients": [_to_dict(c) for c in result.scalars().all()]}


@router.post("")
async def create_client(payload: ClientRequest, db: AsyncSession = Depends(get_db)):
    c = ClientDB(**payload.model_dump())
    db.add(c)
    await db.commit()
    await db.refresh(c)
    return _to_dict(c)


@router.get("/{client_id}")
async def get_client(client_id: str, db: AsyncSession = Depends(get_db)):
    c = await db.get(ClientDB, client_id)
    if not c:
        raise HTTPException(status_code=404, detail="Client introuvable")
    return _to_dict(c)


@router.put("/{client_id}")
async def update_client(client_id: str, payload: ClientRequest, db: AsyncSession = Depends(get_db)):
    c = await db.get(ClientDB, client_id)
    if not c:
        raise HTTPException(status_code=404, detail="Client introuvable")
    for k, v in payload.model_dump().items():
        setattr(c, k, v)
    await db.commit()
    await db.refresh(c)
    return _to_dict(c)


@router.delete("/{client_id}")
async def delete_client(client_id: str, db: AsyncSession = Depends(get_db)):
    c = await db.get(ClientDB, client_id)
    if not c:
        raise HTTPException(status_code=404, detail="Client introuvable")
    c.is_active = False
    await db.commit()
    return {"deleted": True, "id": client_id}


@router.get("/{client_id}/dossiers")
async def client_dossiers(client_id: str, db: AsyncSession = Depends(get_db)):
    c = await db.get(ClientDB, client_id)
    if not c:
        raise HTTPException(status_code=404, detail="Client introuvable")

    stmt = select(DossierDB)
    conds = []
    if c.email:
        conds.append(DossierDB.client_email == c.email)
    if c.nom:
        conds.append(DossierDB.client_nom == c.nom)
    if not conds:
        return {"dossiers": []}
    stmt = stmt.where(or_(*conds)).order_by(DossierDB.created_at.desc())
    result = await db.execute(stmt)
    return {
        "dossiers": [
            {
                "id": d.id,
                "reference": getattr(d, "reference", None),
                "client_nom": d.client_nom,
                "statut": getattr(d, "statut", None),
                "created_at": d.created_at.isoformat() if d.created_at else None,
            }
            for d in result.scalars().all()
        ]
    }
