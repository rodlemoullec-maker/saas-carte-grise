"""
Router dossiers — version locale d'AutoDoc Pro.

POST   /dossiers/                       Créer un dossier (saisie agent)
GET    /dossiers/                       Lister les dossiers de l'agent
GET    /dossiers/{id}                   Détail d'un dossier
GET    /dossiers/{id}/checklist         Checklist d'avancement
POST   /dossiers/{id}/run-diagnostic    Lancer le diagnostic complet
GET    /dossiers/{id}/cerfa             Générer / récupérer le Cerfa (100% PIL)
GET    /dossiers/{id}/relance-email     Email de relance pré-rédigé (à copier-coller)
GET    /dossiers/{id}/admin             Vue admin/debug du dossier
GET    /dossiers/{id}/download-zip      Télécharger le dossier complet en ZIP
DELETE /dossiers/{id}                   Supprimer un dossier
"""
from __future__ import annotations

import logging
import random
import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.dependencies import get_current_agent
from api.models.base import get_db
from api.models.dossier import DossierDB
from api.schemas.dossier import DossierCreateRequest

logger = logging.getLogger(__name__)

router = APIRouter()


def _generate_reference() -> str:
    year = datetime.utcnow().year
    seq = random.randint(10000, 99999)
    return f"CG-{year}-{seq}"


def _to_response(d: DossierDB) -> dict:
    return {
        "id": d.id,
        "reference": d.reference,
        "type": d.type,
        "status": d.status,
        "diagnostic": d.diagnostic,
        "vin": d.vin,
        "immatriculation": d.immatriculation,
        "client_nom": d.client_nom,
        "client_prenom": d.client_prenom,
        "tax_estimate": d.tax_estimate,
        "created_at": d.created_at,
        "updated_at": d.updated_at,
    }


# ─── CRUD ────────────────────────────────────────────────────────────────────


@router.post("/", status_code=201)
async def create_dossier(
    request: DossierCreateRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Crée un dossier vide. L'agent l'alimente ensuite par drag & drop d'emails
    ou en uploadant directement les documents.
    """
    agent = await get_current_agent(db)
    if not agent:
        raise HTTPException(404, "Aucun agent configuré sur cette installation")
    if not agent.setup_complete:
        raise HTTPException(422, detail={
            "error": "profil_incomplet",
            "message": (
                "Le profil de l'agent n'est pas complet. "
                "Renseignez votre raison sociale, adresse, numéro d'habilitation, "
                "puis uploadez votre cachet et signature avant de créer un dossier."
            ),
        })

    dossier = DossierDB(
        id=str(uuid.uuid4()),
        reference=_generate_reference(),
        type=None,  # Déduit auto après upload des docs véhicule
        status="PENDING",
        professionnel_id=agent.id,
        client_nom=request.client_nom,
        client_prenom=request.client_prenom,
        client_email=request.client_email,
        client_telephone=request.client_telephone,
        agent_notes=request.notes,
        metadata_={},
    )
    db.add(dossier)
    await db.flush()

    return {
        "dossier_id": dossier.id,
        "reference": dossier.reference,
        "status": "PENDING",
        "message": "Dossier créé. Glissez maintenant les documents (email ou fichiers).",
    }


@router.get("/")
async def list_dossiers(
    status: str | None = None,
    limit: int = Query(default=50, le=200),
    offset: int = Query(default=0, ge=0),
    db: AsyncSession = Depends(get_db),
):
    """Liste les dossiers de l'agent local (un seul agent par installation)."""
    query = select(DossierDB).order_by(DossierDB.created_at.desc())
    if status:
        query = query.where(DossierDB.status == status)
    query = query.offset(offset).limit(limit)
    result = await db.execute(query)
    return [_to_response(d) for d in result.scalars().all()]


@router.get("/{dossier_id}")
async def get_dossier(dossier_id: str, db: AsyncSession = Depends(get_db)):
    dossier = await db.get(DossierDB, dossier_id)
    if not dossier:
        raise HTTPException(404, "Dossier non trouvé")
    return _to_response(dossier)


@router.delete("/{dossier_id}", status_code=204)
async def delete_dossier(dossier_id: str, db: AsyncSession = Depends(get_db)):
    """Supprime un dossier et tous ses documents associés."""
    dossier = await db.get(DossierDB, dossier_id)
    if not dossier:
        raise HTTPException(404, "Dossier non trouvé")

    # Supprimer les fichiers chiffrés du store local
    from storage.document_store import get_document_store
    store = get_document_store()
    for doc in dossier.documents:
        try:
            await store.delete(doc.storage_path)
        except Exception as e:
            logger.warning(f"Suppression fichier {doc.storage_path} échouée : {e}")

    await db.delete(dossier)
    await db.flush()
    return None


# ─── Checklist ───────────────────────────────────────────────────────────────


@router.get("/{dossier_id}/checklist")
async def get_checklist(dossier_id: str, db: AsyncSession = Depends(get_db)):
    """Checklist d'avancement du dossier (documents reçus, manquants, problèmes)."""
    dossier = await db.get(DossierDB, dossier_id)
    if not dossier:
        raise HTTPException(404, "Dossier non trouvé")

    from api.routers.documents import _build_dossier_dict
    from engine.pipeline.realtime import _check_pro_docs, _check_client_docs

    dossier_dict = await _build_dossier_dict(db, dossier)
    pro_checklist = _check_pro_docs(dossier_dict)
    client_checklist = _check_client_docs(dossier_dict)
    pro_checklist["client_docs"] = client_checklist
    return pro_checklist


# ─── Diagnostic ──────────────────────────────────────────────────────────────


@router.post("/{dossier_id}/run-diagnostic")
async def run_diagnostic_endpoint(dossier_id: str, db: AsyncSession = Depends(get_db)):
    """Lance le diagnostic complet — vérifie tous les documents et croise."""
    dossier = await db.get(DossierDB, dossier_id)
    if not dossier:
        raise HTTPException(404, "Dossier non trouvé")

    from api.routers.documents import _build_dossier_dict
    from engine.pipeline.realtime import _check_cerfa_blocages, run_diagnostic

    dossier_dict = await _build_dossier_dict(db, dossier)
    blocages = _check_cerfa_blocages(dossier_dict)
    if blocages["blocked"]:
        raise HTTPException(422, detail={
            "error": "diagnostic_bloque",
            "message": "Le dossier ne peut pas être diagnostiqué — il manque des éléments.",
            "blocages": blocages["reasons"],
        })

    result = run_diagnostic(dossier_dict)
    dossier.diagnostic = result["diagnostic"]
    dossier.blocages = result.get("blocages")
    dossier.tax_estimate = result.get("tax_estimate")
    dossier.status = "DIAGNOSTIC"
    await db.flush()
    return result


# ─── Email de relance pré-rédigé ─────────────────────────────────────────────


@router.get("/{dossier_id}/relance-email")
async def get_relance_email(dossier_id: str, db: AsyncSession = Depends(get_db)):
    """
    Génère le texte d'un email de relance pour ce dossier.

    L'agent reçoit un sujet + un corps prêt à coller dans son client email
    habituel (Gmail, Outlook, Thunderbird). Aucun email n'est envoyé par
    AutoDoc Pro — l'éditeur n'a accès à aucune communication.

    Si le dossier est en VERT (complet), retourne un email "Cerfa prêt".
    Sinon, retourne un email de relance personnalisé avec la liste des
    points à corriger, dérivée des codes de blocage du diagnostic.
    """
    dossier = await db.get(DossierDB, dossier_id)
    if not dossier:
        raise HTTPException(404, "Dossier non trouvé")

    agent = await get_current_agent(db)
    if not agent:
        raise HTTPException(404, "Aucun agent configuré sur cette installation")

    from notifications.relance_emails import generate_relance_email
    return generate_relance_email(dossier=dossier, agent=agent)


# ─── Génération du Cerfa (100% PIL local) ────────────────────────────────────


@router.get("/{dossier_id}/cerfa")
async def generate_cerfa_endpoint(dossier_id: str, db: AsyncSession = Depends(get_db)):
    """
    Génère ou récupère le Cerfa pré-rempli (PDF).

    100% local via PIL — aucun appel à service-public.gouv.fr ni à un service en ligne.
    """
    from fastapi.responses import Response
    from storage.document_store import get_document_store

    dossier = await db.get(DossierDB, dossier_id)
    if not dossier:
        raise HTTPException(404, "Dossier non trouvé")

    dossier_type = "VN" if (dossier.type or "").upper() == "VN" else "VO"
    cerfa_num = "13749" if dossier_type == "VN" else "13750"
    cerfa_path = f"{dossier_id}/cerfa/Cerfa_{cerfa_num}.pdf"
    store = get_document_store()

    # Si déjà généré → servir le PDF
    if dossier.cerfa_generated:
        try:
            pdf_bytes = await store.get(cerfa_path)
            return Response(
                content=pdf_bytes,
                media_type="application/pdf",
                headers={"Content-Disposition": f'inline; filename="Cerfa_{cerfa_num}.pdf"'},
            )
        except FileNotFoundError:
            pass  # Régénérer ci-dessous

    # Vérifier les blocages
    from api.routers.documents import _build_dossier_dict
    from engine.pipeline.realtime import _check_cerfa_blocages

    dossier_dict = await _build_dossier_dict(db, dossier)
    blocages = _check_cerfa_blocages(dossier_dict)
    if blocages["blocked"]:
        raise HTTPException(422, detail={
            "error": "cerfa_bloque",
            "message": "Le Cerfa ne peut pas être généré — il manque des éléments.",
            "blocages": blocages["reasons"],
        })

    # Génération PIL locale
    import asyncio
    from engine.cerfa_automation.cerfa_filler import CerfaFiller

    cerfa_data = CerfaFiller.build_data_from_dossier(dossier_dict)
    metadata = dossier.metadata_ or {}
    cnit_manuel = metadata.get("cnit_manuel")
    if cnit_manuel:
        cerfa_data.setdefault("vehicule", {})["cnit"] = cnit_manuel

    try:
        filler = CerfaFiller()
        pdf_bytes = await asyncio.to_thread(
            filler.fill_and_download, cerfa_data, None, dossier_type
        )
    except Exception as e:
        logger.error(f"Erreur génération Cerfa : {e}")
        raise HTTPException(500, detail={
            "error": "cerfa_generation_failed",
            "message": f"Erreur lors de la génération du Cerfa : {e}",
        })

    await store.save(pdf_bytes, cerfa_path, "application/pdf")
    dossier.cerfa_generated = True
    dossier.status = "CERFA_GENERE"
    await db.flush()

    # Cleanup RGPD : supprimer les données client sensibles après génération
    try:
        from engine.rgpd.cleanup import cleanup_client_data_after_cerfa
        await cleanup_client_data_after_cerfa(db, dossier_id)
    except Exception as e:
        logger.warning(f"[RGPD] Cleanup échoué : {e}")

    return {
        "status": "ok",
        "message": "Cerfa généré. Vous pouvez le télécharger et le soumettre au SIV.",
        "dossier_id": dossier_id,
        "cerfa_type": cerfa_num,
    }


# ─── Vue admin ───────────────────────────────────────────────────────────────


@router.get("/{dossier_id}/admin")
async def admin_view(dossier_id: str, db: AsyncSession = Depends(get_db)):
    """Vue complète du dossier (debug, métadonnées, documents)."""
    dossier = await db.get(DossierDB, dossier_id)
    if not dossier:
        raise HTTPException(404, "Dossier non trouvé")

    from api.routers.documents import _build_dossier_dict
    dossier_dict = await _build_dossier_dict(db, dossier)

    return {
        "id": dossier.id,
        "reference": dossier.reference,
        "type": dossier.type,
        "status": dossier.status,
        "diagnostic": dossier.diagnostic,
        "vin": dossier.vin,
        "immatriculation": dossier.immatriculation,
        "client_nom": dossier.client_nom,
        "client_prenom": dossier.client_prenom,
        "client_telephone": dossier.client_telephone,
        "client_email": dossier.client_email,
        "is_personne_morale": dossier.is_personne_morale,
        "is_mineur": dossier.is_mineur,
        "is_etranger": dossier.is_etranger,
        "documents_vendeur": dossier_dict.get("documents_vendeur", []),
        "documents_client": dossier_dict.get("documents_client", []),
        "blocages": dossier.blocages,
        "tax_estimate": dossier.tax_estimate,
        "cerfa_generated": dossier.cerfa_generated,
        "agent_notes": dossier.agent_notes,
        "created_at": dossier.created_at.isoformat() if dossier.created_at else None,
        "updated_at": dossier.updated_at.isoformat() if dossier.updated_at else None,
    }


# ─── Téléchargement ZIP ──────────────────────────────────────────────────────


@router.get("/{dossier_id}/download-zip")
async def download_dossier_zip(dossier_id: str, db: AsyncSession = Depends(get_db)):
    """Télécharge tous les documents du dossier dans un ZIP."""
    import io
    import zipfile
    from fastapi.responses import StreamingResponse
    from storage.document_store import get_document_store

    dossier = await db.get(DossierDB, dossier_id)
    if not dossier:
        raise HTTPException(404, "Dossier non trouvé")

    store = get_document_store()
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        # Documents
        for doc in dossier.documents:
            try:
                file_bytes = await store.get(doc.storage_path)
                arcname = f"documents/{doc.type}/{doc.original_filename}"
                zf.writestr(arcname, file_bytes)
            except FileNotFoundError:
                logger.warning(f"Document introuvable : {doc.storage_path}")

        # Cerfa si généré
        if dossier.cerfa_generated:
            dossier_type = "VN" if (dossier.type or "").upper() == "VN" else "VO"
            cerfa_num = "13749" if dossier_type == "VN" else "13750"
            cerfa_path = f"{dossier_id}/cerfa/Cerfa_{cerfa_num}.pdf"
            try:
                pdf_bytes = await store.get(cerfa_path)
                zf.writestr(f"cerfa/Cerfa_{cerfa_num}.pdf", pdf_bytes)
            except FileNotFoundError:
                pass

    buf.seek(0)
    return StreamingResponse(
        iter([buf.read()]),
        media_type="application/zip",
        headers={
            "Content-Disposition": f'attachment; filename="dossier_{dossier.reference}.zip"',
        },
    )
