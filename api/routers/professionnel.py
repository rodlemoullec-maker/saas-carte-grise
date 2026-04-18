"""
Router agent — paramétrage du profil unique de l'agent local.

GET    /agent              Récupérer le profil de l'agent
POST   /agent              Créer ou mettre à jour le profil
POST   /agent/cachet       Uploader le cachet commercial
POST   /agent/signature    Uploader la signature
POST   /agent/kbis         Uploader le Kbis

Version locale : il n'y a qu'UN SEUL agent par installation.
Le concept de "type_compte" et de relations vendeur/agent a été supprimé.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, UploadFile
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.models.base import get_db
from api.models.professionnel import Professionnel
from storage.document_store import get_document_store

router = APIRouter(prefix="/agent", tags=["agent"])


class AgentProfileRequest(BaseModel):
    raison_sociale: str
    siret: str | None = None
    siren: str | None = None
    email: str
    telephone: str | None = None
    adresse: str | None = None
    code_postal: str | None = None
    ville: str | None = None
    nom_commerce: str | None = None
    telephone_commerce: str | None = None
    email_commerce: str | None = None
    numero_habilitation: str | None = None


def _profile_to_dict(pro: Professionnel) -> dict:
    return {
        "id": pro.id,
        "raison_sociale": pro.raison_sociale,
        "siret": pro.siret,
        "siren": pro.siren,
        "email": pro.email,
        "telephone": pro.telephone,
        "adresse": pro.adresse,
        "code_postal": pro.code_postal,
        "ville": pro.ville,
        "nom_commerce": pro.nom_commerce,
        "telephone_commerce": pro.telephone_commerce,
        "email_commerce": pro.email_commerce,
        "habilite_siv": pro.habilite_siv,
        "numero_habilitation": pro.numero_habilitation,
        "cachet_path": pro.cachet_path,
        "signature_path": pro.signature_path,
        "kbis_path": pro.kbis_path,
        "setup_complete": pro.setup_complete,
    }


def _update_setup_complete(pro: Professionnel) -> None:
    """Marque le profil complet si toutes les infos minimales sont là."""
    pro.setup_complete = bool(
        pro.raison_sociale
        and pro.email
        and pro.nom_commerce
        and pro.adresse
        and pro.cachet_path
        and pro.numero_habilitation
    )


async def _get_or_create_agent(db: AsyncSession) -> Professionnel:
    """
    Récupère l'unique agent local. S'il n'existe pas (premier démarrage),
    en crée un par défaut que l'utilisateur complétera ensuite.
    """
    result = await db.execute(select(Professionnel).limit(1))
    pro = result.scalar_one_or_none()
    if pro is None:
        pro = Professionnel(
            raison_sociale="(Mon cabinet)",
            email="agent@local",
            habilite_siv=True,
        )
        db.add(pro)
        await db.flush()
    return pro


@router.get("")
async def get_agent(db: AsyncSession = Depends(get_db)):
    """Récupère le profil de l'agent local."""
    pro = await _get_or_create_agent(db)
    return _profile_to_dict(pro)


@router.post("")
async def update_agent(
    req: AgentProfileRequest,
    db: AsyncSession = Depends(get_db),
):
    """Crée ou met à jour le profil de l'agent local."""
    pro = await _get_or_create_agent(db)

    pro.raison_sociale = req.raison_sociale
    pro.siret = req.siret
    pro.siren = req.siren
    pro.email = req.email
    pro.telephone = req.telephone
    pro.adresse = req.adresse
    pro.code_postal = req.code_postal
    pro.ville = req.ville
    pro.nom_commerce = req.nom_commerce
    pro.telephone_commerce = req.telephone_commerce
    pro.email_commerce = req.email_commerce
    pro.numero_habilitation = req.numero_habilitation

    _update_setup_complete(pro)
    await db.flush()

    return {
        "status": "ok",
        "setup_complete": pro.setup_complete,
        "agent": _profile_to_dict(pro),
    }


@router.post("/cachet")
async def upload_cachet(
    file: UploadFile,
    db: AsyncSession = Depends(get_db),
):
    """Upload le cachet commercial (image PNG/JPG)."""
    pro = await _get_or_create_agent(db)
    content = await file.read()
    if not content:
        raise HTTPException(422, "Fichier vide")

    store = get_document_store()
    path = f"agent/cachet_{pro.id}.bin"
    await store.save(content, path, file.content_type or "image/png")
    pro.cachet_path = path

    _update_setup_complete(pro)
    await db.flush()
    return {"status": "ok", "cachet_path": path}


@router.post("/signature")
async def upload_signature(
    file: UploadFile,
    db: AsyncSession = Depends(get_db),
):
    """Upload la signature (image PNG/JPG)."""
    pro = await _get_or_create_agent(db)
    content = await file.read()
    if not content:
        raise HTTPException(422, "Fichier vide")

    store = get_document_store()
    path = f"agent/signature_{pro.id}.bin"
    await store.save(content, path, file.content_type or "image/png")
    pro.signature_path = path

    _update_setup_complete(pro)
    await db.flush()
    return {"status": "ok", "signature_path": path}


@router.post("/kbis")
async def upload_kbis(
    file: UploadFile,
    db: AsyncSession = Depends(get_db),
):
    """Upload le Kbis (PDF ou image)."""
    pro = await _get_or_create_agent(db)
    content = await file.read()
    if not content:
        raise HTTPException(422, "Fichier vide")

    store = get_document_store()
    path = f"agent/kbis_{pro.id}.bin"
    await store.save(content, path, file.content_type or "application/pdf")
    pro.kbis_path = path

    _update_setup_complete(pro)
    await db.flush()
    return {"status": "ok", "kbis_path": path}
