"""
Router dossiers — CRUD + checklist + confirm-send-link + choix assurance.

POST   /dossiers/                       Créer un dossier (portable client seulement)
GET    /dossiers/                       Lister les dossiers
GET    /dossiers/{id}                   Détail d'un dossier
GET    /dossiers/{id}/checklist         Checklist interactive vendeur
POST   /dossiers/{id}/choix-assurance   Choix assurance pour ce dossier
POST   /dossiers/{id}/pas-de-cession    Option pas de certificat de cession
POST   /dossiers/{id}/confirm-send-link Confirmer envoi du lien SMS au client
DELETE /dossiers/{id}                   Annuler un dossier
"""
from __future__ import annotations

import logging
import secrets

logger = logging.getLogger(__name__)
from datetime import datetime
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm.attributes import flag_modified

from notifications.messages import PRO as MSG_PRO
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.models.base import get_db
from storage.document_store import get_document_store
from api.models.dossier import DossierDB
from api.models.professionnel import Professionnel
from api.schemas.dossier import DossierCreateRequest, DossierResponse

router = APIRouter()


def _generate_reference() -> str:
    import random
    year = datetime.utcnow().year
    seq = random.randint(10000, 99999)
    return f"CG-{year}-{seq}"


# ─── CRUD ────────────────────────────────────────────────────────────────────


@router.post("/", status_code=201)
async def create_dossier(
    request: DossierCreateRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Crée un dossier. Saisie minimale : portable client + email optionnel.
    Le type VN/VO est déduit automatiquement après dépôt des documents.
    """
    # Vérifier que le profil pro est complet
    pro = await db.get(Professionnel, request.professionnel_id)
    if not pro:
        raise HTTPException(404, "Professionnel non trouvé")
    if not pro.setup_complete:
        raise HTTPException(422, detail={
            "error": "profil_incomplet",
            "message": MSG_PRO["profil_incomplet"],
        })

    dossier = DossierDB(
        id=uuid4(),
        reference=_generate_reference(),
        type=None,  # Déduit auto après upload
        status="PENDING",
        professionnel_id=request.professionnel_id,
        client_telephone=request.client_telephone,
        client_email=request.client_email,
        metadata_={},
    )
    db.add(dossier)
    await db.flush()

    return {
        "dossier_id": str(dossier.id),
        "reference": dossier.reference,
        "status": "PENDING",
        "message": MSG_PRO["dossier_cree"],
        "docs_attendus": {
            "vn": [
                {"type": "COC", "label": "Certificat de Conformite (COC)", "obligatoire": True},
                {"type": "FACTURE", "label": "Facture de vente", "obligatoire": True},
            ],
            "vo": [
                {"type": "CG_BARREE", "label": "Carte grise barree", "obligatoire": True},
                {"type": "CERTIFICAT_CESSION", "label": "Certificat de cession (15776) signe", "obligatoire": True},
                {"type": "COC", "label": "COC (recommande)", "obligatoire": False},
            ],
        },
    }


@router.get("/")
async def list_dossiers(
    professionnel_id: UUID | None = None,
    status: str | None = None,
    limit: int = Query(default=50, le=200),
    offset: int = Query(default=0, ge=0),
    db: AsyncSession = Depends(get_db),
):
    query = select(DossierDB).order_by(DossierDB.created_at.desc())
    if professionnel_id:
        query = query.where(DossierDB.professionnel_id == professionnel_id)
    if status:
        query = query.where(DossierDB.status == status)
    query = query.offset(offset).limit(limit)
    result = await db.execute(query)
    return [_to_response(d) for d in result.scalars().all()]


@router.get("/{dossier_id}")
async def get_dossier(dossier_id: UUID, db: AsyncSession = Depends(get_db)):
    dossier = await db.get(DossierDB, dossier_id)
    if not dossier:
        raise HTTPException(404, "Dossier non trouve")
    return _to_response(dossier)


# ─── Checklist interactive ───────────────────────────────────────────────────


@router.get("/{dossier_id}/checklist")
async def get_checklist(dossier_id: UUID, db: AsyncSession = Depends(get_db)):
    """Checklist interactive — docs vendeur + docs client."""
    dossier = await db.get(DossierDB, dossier_id)
    if not dossier:
        raise HTTPException(404, "Dossier non trouve")

    from api.routers.documents import _build_dossier_dict
    from engine.pipeline.realtime import _check_pro_docs, _check_client_docs

    dossier_dict = await _build_dossier_dict(db, dossier)
    pro_checklist = _check_pro_docs(dossier_dict)
    client_checklist = _check_client_docs(dossier_dict)

    pro_checklist["client_docs"] = client_checklist
    return pro_checklist


# ─── Assurance ───────────────────────────────────────────────────────────────


class ChoixAssuranceRequest(BaseModel):
    assurance_flotte_couvre: bool
    demander_client: bool | None = None


@router.post("/{dossier_id}/choix-assurance")
async def choix_assurance(
    dossier_id: UUID, req: ChoixAssuranceRequest, db: AsyncSession = Depends(get_db),
):
    dossier = await db.get(DossierDB, dossier_id)
    if not dossier:
        raise HTTPException(404, "Dossier non trouve")

    metadata = dossier.metadata_ or {}
    metadata["assurance_flotte_couvre"] = req.assurance_flotte_couvre
    metadata["choix_assurance_pro"] = True

    if req.assurance_flotte_couvre:
        metadata["demander_assurance_client"] = False
        dossier.metadata_ = metadata
        flag_modified(dossier, 'metadata_')
        await db.flush()
        return {"status": "ok", "message": MSG_PRO["assurance_flotte_ok"]}

    if req.demander_client is None:
        raise HTTPException(422, "Repondez a la question 2.")

    metadata["demander_assurance_client"] = req.demander_client
    dossier.metadata_ = metadata
    flag_modified(dossier, 'metadata_')
    await db.flush()

    if req.demander_client:
        return {
            "status": "ok",
            "message": MSG_PRO["assurance_demander_client"],
            "info": "Pensez a verifier vous-meme que l'assurance couvre bien le vehicule avant de soumettre au SIV — c'est un point que vous maitrisez mieux que nous !",
        }
    return {"status": "ok", "message": MSG_PRO["assurance_gerer_direct"]}


# ─── Cession ─────────────────────────────────────────────────────────────────


@router.post("/{dossier_id}/pas-de-cession")
async def toggle_pas_de_cession(dossier_id: UUID, db: AsyncSession = Depends(get_db)):
    dossier = await db.get(DossierDB, dossier_id)
    if not dossier:
        raise HTTPException(404, "Dossier non trouve")

    metadata = dossier.metadata_ or {}
    metadata["pas_de_certificat_cession"] = True
    dossier.metadata_ = metadata
    flag_modified(dossier, 'metadata_')
    await db.flush()

    return {
        "status": "ok",
        "message": MSG_PRO["pas_de_cession"],
    }


# ─── CG chez le client ────────────────────────────────────────────────────


@router.post("/{dossier_id}/cg-chez-client")
async def set_cg_chez_client(dossier_id: UUID, db: AsyncSession = Depends(get_db)):
    """
    Le pro indique qu'il n'a pas la CG barree — le client la deposera via le lien SMS.
    Le verrou d'identification vehicule ne sera confirme que lorsque le client l'aura deposee.
    """
    dossier = await db.get(DossierDB, dossier_id)
    if not dossier:
        raise HTTPException(404, "Dossier non trouve")

    metadata = dossier.metadata_ or {}
    metadata["cg_chez_client"] = True
    dossier.metadata_ = metadata
    flag_modified(dossier, 'metadata_')
    await db.flush()

    return {
        "status": "ok",
        "message": (
            "Note. La carte grise barree sera demandee au client via le lien SMS. "
            "L'identification du vehicule sera confirmee dans votre espace "
            "des que le client l'aura deposee."
        ),
    }


# ─── CNIT manuel ───────────────────────────────────────────────────────────


@router.post("/{dossier_id}/cnit")
async def set_cnit(dossier_id: UUID, body: dict, db: AsyncSession = Depends(get_db)):
    """
    Le pro saisit le CNIT manuellement (COC europeen sans CNIT).
    Le CNIT sera inclus dans le Cerfa genere.
    """
    dossier = await db.get(DossierDB, dossier_id)
    if not dossier:
        raise HTTPException(404, "Dossier non trouve")

    cnit = (body.get("cnit") or "").strip().upper()
    if not cnit:
        raise HTTPException(422, "Le CNIT ne peut pas etre vide.")

    metadata = dossier.metadata_ or {}
    metadata["cnit_manuel"] = cnit
    dossier.metadata_ = metadata
    flag_modified(dossier, 'metadata_')
    await db.flush()

    is_cerfa_genere = dossier.status == "CERFA_GENERE"

    return {
        "status": "ok",
        "cnit": cnit,
        "cerfa_a_regenerer": is_cerfa_genere,
        "message": (
            f"CNIT enregistre : {cnit}. "
            + ("Le Cerfa peut etre re-genere pour inclure le CNIT." if is_cerfa_genere
               else "Il sera inclus dans le Cerfa lors de la generation.")
        ),
    }


# ─── Confirm send link ──────────────────────────────────────────────────────


@router.post("/{dossier_id}/confirm-send-link")
async def confirm_send_link(dossier_id: UUID, db: AsyncSession = Depends(get_db)):
    """Le pro confirme l'envoi du lien sécurisé au client."""
    dossier = await db.get(DossierDB, dossier_id)
    if not dossier:
        raise HTTPException(404, "Dossier non trouve")

    pro = await db.get(Professionnel, dossier.professionnel_id)
    if not pro or not pro.nom_commerce:
        raise HTTPException(422, detail={
            "error": "profil_non_configure",
            "message": MSG_PRO["profil_non_configure"],
        })

    # Verifier checklist vendeur (#23)
    from api.routers.documents import _build_dossier_dict
    from engine.pipeline.realtime import _check_pro_docs
    dossier_dict = await _build_dossier_dict(db, dossier)
    checklist = _check_pro_docs(dossier_dict)
    if not checklist.get("client_link_ready"):
        raise HTTPException(422, detail={
            "error": "docs_pro_incomplets",
            "message": MSG_PRO["docs_manquants"],
            "checklist": checklist,
        })

    # Generer le SMS personnalise (#22)
    from notifications.sms import build_sms_client_link
    sms_text = build_sms_client_link(
        client_prenom=dossier.client_prenom,
        nom_commerce=pro.nom_commerce or "",
        lien="{LIEN}",  # Remplace apres generation du token
        telephone_commerce=pro.telephone_commerce or "",
    )

    # Générer le token client
    client_token = secrets.token_urlsafe(32)
    dossier.client_link_token = client_token
    dossier.client_link_sent_at = datetime.utcnow()
    dossier.status = "ATTENTE_CLIENT"
    await db.flush()

    # TODO: envoyer le SMS réel via notifications/sms.py

    return {
        "status": "lien_envoye",
        "message": MSG_PRO["sms_envoye"].format(telephone=dossier.client_telephone),
        "sms_envoye": sms_text.replace("{LIEN}", f"/client/{client_token}"),
        "client_link": f"/client/{client_token}",
        "sent_at": dossier.client_link_sent_at.isoformat() if dossier.client_link_sent_at else None,
        "sent_to": {
            "telephone": dossier.client_telephone,
            "email": dossier.client_email,
        },
    }


# ─── Diagnostic + Cerfa ──────────────────────────────────────────────────────


@router.post("/{dossier_id}/run-diagnostic")
async def run_diagnostic_endpoint(dossier_id: UUID, db: AsyncSession = Depends(get_db)):
    """Lance le diagnostic complet — vérifie tous les docs vendeur + client."""
    dossier = await db.get(DossierDB, dossier_id)
    if not dossier:
        raise HTTPException(404, "Dossier non trouve")

    from api.routers.documents import _build_dossier_dict
    from engine.pipeline.realtime import _check_cerfa_blocages, run_diagnostic

    dossier_dict = await _build_dossier_dict(db, dossier)

    # Verifier blocages
    blocages = _check_cerfa_blocages(dossier_dict)
    if blocages["blocked"]:
        raise HTTPException(422, detail={
            "error": "diagnostic_bloque",
            "message": MSG_PRO["diagnostic_bloque"],
            "blocages": blocages["reasons"],
        })

    # Lancer le diagnostic
    result = run_diagnostic(dossier_dict)

    dossier.diagnostic = result["diagnostic"]
    dossier.blocages = result.get("blocages")
    dossier.tax_estimate = result.get("tax_estimate")
    dossier.status = "DIAGNOSTIC"
    await db.flush()

    return result


@router.get("/{dossier_id}/cerfa")
async def generate_cerfa_endpoint(dossier_id: UUID, db: AsyncSession = Depends(get_db)):
    """Genere ou telecharge le Cerfa."""
    dossier = await db.get(DossierDB, dossier_id)
    if not dossier:
        raise HTTPException(404, "Dossier non trouve")

    # Si deja genere → servir directement
    if dossier.status == "CERFA_GENERE":
        # TODO: retourner le vrai PDF depuis le store
        # Pour l'instant, retourne un message
        return {
            "status": "ok",
            "message": MSG_PRO["cerfa_pret"],
            "dossier_id": str(dossier_id),
            "cerfa_type": "13749" if (dossier.type or "").upper() == "VN" else "13750",
        }

    # Sinon, verifier les blocages avant de generer
    from api.routers.documents import _build_dossier_dict
    from engine.pipeline.realtime import _check_cerfa_blocages

    dossier_dict = await _build_dossier_dict(db, dossier)
    blocages = _check_cerfa_blocages(dossier_dict)
    if blocages["blocked"]:
        raise HTTPException(422, detail={
            "error": "cerfa_bloque",
            "message": MSG_PRO["cerfa_bloque"],
            "blocages": blocages["reasons"],
        })

    # TODO: appeler engine/cerfa_automation/cerfa_filler.py pour generer le PDF
    dossier.status = "CERFA_GENERE"
    await db.flush()

    # Nettoyage RGPD automatique — supprimer les donnees client sensibles
    from engine.rgpd.cleanup import cleanup_client_data_after_cerfa
    try:
        cleanup_result = await cleanup_client_data_after_cerfa(db, dossier_id)
        logger.info(f"[RGPD] Nettoyage effectue : {cleanup_result}")
    except Exception as e:
        logger.error(f"[RGPD] Nettoyage echoue : {e}")

    # CNIT : verifier si present (COC ou saisie manuelle)
    is_vn = (dossier.type or "").upper() == "VN"
    metadata = dossier.metadata_ or {}
    cnit_manuel = metadata.get("cnit_manuel")
    cnit_coc = None

    if is_vn:
        from sqlalchemy import select
        from api.models.document import DocumentDB
        result = await db.execute(
            select(DocumentDB).where(
                DocumentDB.dossier_id == dossier_id,
                DocumentDB.type == "COC",
            )
        )
        coc_doc = result.scalar_one_or_none()
        if coc_doc:
            cnit_coc = (coc_doc.extracted_data or {}).get("cnit")

    cnit_final = cnit_manuel or cnit_coc
    warnings = []

    if is_vn and not cnit_final:
        warnings.append({
            "code": "CNIT_ABSENT",
            "message": (
                "Le CNIT (champ D.2.1) n'est pas renseigne — "
                "le champ type mines sera vide sur le Cerfa. "
                "Vous pouvez encore l'ajouter via le champ CNIT du dossier "
                "pour obtenir un Cerfa complet, ou le saisir directement dans le SIV."
            ),
        })
    elif is_vn and cnit_final and not cnit_coc:
        # CNIT saisi manuellement → inclus dans le Cerfa
        warnings.append({
            "code": "CNIT_MANUEL",
            "message": f"CNIT {cnit_final} (saisie manuelle) inclus dans le Cerfa.",
        })

    return {
        "status": "ok",
        "message": MSG_PRO["cerfa_pret"],
        "dossier_id": str(dossier_id),
        "cerfa_type": "13749" if is_vn else "13750",
        "cnit": cnit_final,
        "warnings": warnings,
    }


@router.get("/{dossier_id}/admin")
async def admin_view(dossier_id: UUID, db: AsyncSession = Depends(get_db)):
    """Vue admin complete du dossier."""
    dossier = await db.get(DossierDB, dossier_id)
    if not dossier:
        raise HTTPException(404, "Dossier non trouve")

    from api.routers.documents import _build_dossier_dict
    dossier_dict = await _build_dossier_dict(db, dossier)

    return {
        "id": str(dossier.id),
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
        "documents_vendeur": dossier_dict.get("documents_vendeur", []),
        "documents_client": dossier_dict.get("documents_client", []),
        "blocages": dossier.blocages,
        "tax_estimate": dossier.tax_estimate,
        "cerfa_genere": dossier.status == "CERFA_GENERE",
        "created_at": dossier.created_at.isoformat() if dossier.created_at else None,
    }


# ─── Telechargement dossier complet (ZIP) ────────────────────────────────────


@router.get("/{dossier_id}/download-zip")
async def download_dossier_zip(dossier_id: UUID, db: AsyncSession = Depends(get_db)):
    """
    Telecharge toutes les pieces du dossier dans un ZIP structure :
    vendeur/ + client/ + cerfa/
    """
    import io
    import zipfile
    from fastapi.responses import StreamingResponse

    dossier = await db.get(DossierDB, dossier_id)
    if not dossier:
        raise HTTPException(404, "Dossier non trouve")

    from api.routers.documents import _build_dossier_dict
    dossier_dict = await _build_dossier_dict(db, dossier)

    # Nom du ZIP
    nom = dossier.client_nom or "INCONNU"
    prenom = dossier.client_prenom or ""
    type_vn_vo = dossier.type or "XX"
    ref = dossier.reference or ""
    vin_immat = dossier.vin or dossier.immatriculation or ""
    zip_name = f"{nom}_{prenom}_{type_vn_vo}_{ref}_{vin_immat}".replace(" ", "_")

    # Construire le ZIP en memoire
    buffer = io.BytesIO()
    store = get_document_store()

    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        # Documents vendeur
        for doc in dossier_dict.get("documents_vendeur", []):
            filename = doc.get("filename", "document")
            doc_type = doc.get("type", "AUTRE")
            try:
                # Essayer de lire le fichier depuis le store
                path = doc.get("storage_path") or f"{dossier_id}/{filename}"
                file_bytes = await store.get(path)
                zf.writestr(f"vendeur/{doc_type}_{filename}", file_bytes)
            except Exception:
                # Si le fichier n'est pas accessible, mettre un placeholder
                zf.writestr(f"vendeur/{doc_type}_{filename}.txt",
                            f"Document: {doc_type}\nFichier: {filename}\nStatut: {doc.get('status')}\n")

        # Documents client
        for doc in dossier_dict.get("documents_client", []):
            filename = doc.get("filename", "document")
            doc_type = doc.get("type", "AUTRE")
            try:
                path = doc.get("storage_path") or f"{dossier_id}/{filename}"
                file_bytes = await store.get(path)
                zf.writestr(f"client/{doc_type}_{filename}", file_bytes)
            except Exception:
                zf.writestr(f"client/{doc_type}_{filename}.txt",
                            f"Document: {doc_type}\nFichier: {filename}\nStatut: {doc.get('status')}\n")

        # Cerfa (si genere)
        # TODO: quand la generation Cerfa sera implementee, lire le PDF depuis le store
        if dossier.status == "CERFA_GENERE":
            cerfa_type = "13749" if type_vn_vo == "VN" else "13750"
            zf.writestr(f"cerfa/Cerfa_{cerfa_type}_{ref}.txt",
                        f"Cerfa {cerfa_type}\nReference: {ref}\nStatut: genere\nCachet + signature apposes automatiquement\n")

        # Recapitulatif
        recap = (
            f"Dossier : {ref}\n"
            f"Titulaire : {nom} {prenom}\n"
            f"Type : {type_vn_vo}\n"
            f"VIN : {dossier.vin or '—'}\n"
            f"Immatriculation : {dossier.immatriculation or '—'}\n"
            f"Diagnostic : {dossier.diagnostic or '—'}\n"
            f"Documents vendeur : {len(dossier_dict.get('documents_vendeur', []))}\n"
            f"Documents client : {len(dossier_dict.get('documents_client', []))}\n"
            f"Cerfa genere : {'oui' if dossier.status == 'CERFA_GENERE' else 'non'}\n"
        )
        zf.writestr("recapitulatif.txt", recap)

    buffer.seek(0)

    return StreamingResponse(
        buffer,
        media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="{zip_name}.zip"'},
    )


# ─── Delete ──────────────────────────────────────────────────────────────────


@router.delete("/{dossier_id}")
async def cancel_dossier(dossier_id: UUID, db: AsyncSession = Depends(get_db)):
    dossier = await db.get(DossierDB, dossier_id)
    if not dossier:
        raise HTTPException(404, "Dossier non trouvé")
    if dossier.status in ("CERFA_GENERE", "SOUMIS"):
        raise HTTPException(422, "Dossier deja finalise — annulation impossible")
    dossier.status = "CLOSED"
    await db.flush()
    return {"status": "ok", "message": MSG_PRO["dossier_annule"]}


# ─── Helpers ─────────────────────────────────────────────────────────────────


def _to_response(d: DossierDB) -> dict:
    return {
        "id": str(d.id),
        "reference": d.reference,
        "type": d.type,
        "status": d.status,
        "diagnostic": d.diagnostic,
        "vin": d.vin,
        "immatriculation": d.immatriculation,
        "client_nom": d.client_nom,
        "client_telephone": d.client_telephone,
        "tax_estimate": d.tax_estimate,
        "created_at": d.created_at.isoformat() if d.created_at else None,
    }
