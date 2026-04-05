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
    if not pro.cgv_acceptees:
        raise HTTPException(422, detail={
            "error": "cgv_non_acceptees",
            "message": "Vous devez accepter les conditions générales de vente avant de créer un dossier.",
        })

    # Vérifier la limite de volume mensuel
    from api.guards.volume_limit import verifier_volume_mensuel, verifier_facturation
    volume = await verifier_volume_mensuel(db, request.professionnel_id)
    if volume["status"] == "bloque":
        raise HTTPException(429, detail={
            "error": "volume_depasse",
            "message": volume["message"],
        })

    # Vérifier la facturation (essai gratuit + batch de 5)
    facturation = await verifier_facturation(db, request.professionnel_id)
    if facturation["status"] == "bloque":
        raise HTTPException(402, detail={
            "error": "paiement_requis",
            "message": facturation["message"],
            "non_payes": facturation["non_payes"],
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
        "message": MSG_PRO["dossier_cree_agent"] if pro.type_compte == "AGENT_HABILITE" else MSG_PRO["dossier_cree"],
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
    pro = await db.get(Professionnel, dossier.professionnel_id)
    type_compte = pro.type_compte if pro else "VENDEUR_HABILITE"

    pro_checklist = _check_pro_docs(dossier_dict)
    client_checklist = _check_client_docs(dossier_dict)

    pro_checklist["client_docs"] = client_checklist
    pro_checklist["type_compte"] = type_compte

    # Pour un agent habilité, la cession n'est pas générée par le système
    if type_compte == "AGENT_HABILITE":
        pro_checklist["cession_generee_par_systeme"] = False
    else:
        pro_checklist["cession_generee_par_systeme"] = True

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
        type_compte=pro.type_compte or "VENDEUR_HABILITE",
    )

    # Générer le token client
    client_token = secrets.token_urlsafe(32)
    dossier.client_link_token = client_token
    dossier.client_link_sent_at = datetime.utcnow()
    dossier.status = "ATTENTE_CLIENT"
    await db.flush()

    # Construire l'URL client complete
    client_url = f"https://app.autodocpro.fr/client/{client_token}"
    sms_final = sms_text.replace("{LIEN}", client_url)

    # Envoyer le SMS
    from notifications.sms import send_sms
    sms_sent = await send_sms(dossier.client_telephone, sms_final)
    if not sms_sent:
        logger.warning(f"[SMS] Echec envoi pour dossier {dossier_id}")

    return {
        "status": "lien_envoye",
        "message": MSG_PRO["sms_envoye"].format(telephone=dossier.client_telephone),
        "sms_envoye": sms_final,
        "sms_sent": sms_sent,
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

    # Si deja genere → servir le PDF
    if dossier.status == "CERFA_GENERE":
        from fastapi.responses import Response
        dossier_type = "VN" if (dossier.type or "").upper() == "VN" else "VO"
        cerfa_num = "13749" if dossier_type == "VN" else "13750"
        cerfa_path = f"{dossier_id}/cerfa/Cerfa_{cerfa_num}.pdf"
        store = get_document_store()
        try:
            pdf_bytes = await store.get(cerfa_path)
            return Response(
                content=pdf_bytes,
                media_type="application/pdf",
                headers={"Content-Disposition": f'inline; filename="Cerfa_{cerfa_num}.pdf"'},
            )
        except FileNotFoundError:
            # PDF absent du store — regenerer
            pass

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

    # Generer le Cerfa via Playwright (service-public.gouv.fr)
    import asyncio
    from engine.cerfa_automation.cerfa_filler import CerfaFiller

    dossier_type = "VN" if (dossier.type or "").upper() == "VN" else "VO"
    cerfa_data = CerfaFiller.build_data_from_dossier(dossier_dict)

    # CNIT manuel → injecter dans les donnees Cerfa
    metadata = dossier.metadata_ or {}
    cnit_manuel = metadata.get("cnit_manuel")
    if cnit_manuel:
        cerfa_data.setdefault("vehicule", {})["cnit"] = cnit_manuel

    try:
        filler = CerfaFiller(headless=True)
        pdf_bytes = await asyncio.to_thread(
            filler.fill_and_download, cerfa_data, None, dossier_type
        )
    except Exception as e:
        logger.error(f"Erreur generation Cerfa : {e}")
        raise HTTPException(500, detail={
            "error": "cerfa_generation_failed",
            "message": f"Erreur lors de la generation du Cerfa : {e}",
        })

    # Sauvegarder le PDF dans le store
    store = get_document_store()
    cerfa_num = "13749" if dossier_type == "VN" else "13750"
    cerfa_path = f"{dossier_id}/cerfa/Cerfa_{cerfa_num}.pdf"
    await store.save(pdf_bytes, cerfa_path, "application/pdf")

    dossier.status = "CERFA_GENERE"
    await db.flush()

    # Notifier le pro par email
    pro = await db.get(Professionnel, dossier.professionnel_id)
    if pro and pro.email_commerce:
        from notifications.email import send_email
        await send_email(pro.email_commerce, "cerfa_pret", {
            "reference": dossier.reference or "",
        })

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

    # Message adapté selon type_compte
    pro = await db.get(Professionnel, dossier.professionnel_id)
    if pro and pro.type_compte == "VENDEUR_NON_HABILITE":
        cerfa_message = MSG_PRO["cerfa_pret_non_habilite"].format(
            agent_nom=pro.agent_nom or "votre agent habilité"
        )
    else:
        cerfa_message = MSG_PRO["cerfa_pret"]

    return {
        "status": "ok",
        "message": cerfa_message,
        "dossier_id": str(dossier_id),
        "cerfa_type": "13749" if is_vn else "13750",
        "cnit": cnit_final,
        "warnings": warnings,
        "type_compte": pro.type_compte if pro else "VENDEUR_HABILITE",
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

        # Cerfa (si genere) — lire le vrai PDF depuis le store
        if dossier.status == "CERFA_GENERE":
            cerfa_type = "13749" if type_vn_vo == "VN" else "13750"
            cerfa_path = f"{dossier_id}/cerfa/Cerfa_{cerfa_type}.pdf"
            try:
                cerfa_bytes = await store.get(cerfa_path)
                zf.writestr(f"cerfa/Cerfa_{cerfa_type}_{ref}.pdf", cerfa_bytes)
            except FileNotFoundError:
                zf.writestr(f"cerfa/Cerfa_{cerfa_type}_{ref}.txt",
                            f"Cerfa {cerfa_type}\nReference: {ref}\nPDF non disponible — relancer la generation.\n")

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


# ─── Paiement Stripe ────────────────────────────────────────────────────────


@router.post("/{dossier_id}/checkout")
async def create_checkout(dossier_id: UUID, db: AsyncSession = Depends(get_db)):
    """
    Cree une session Stripe Checkout pour le paiement des honoraires.
    Retourne l'URL de redirection vers Stripe.
    """
    dossier = await db.get(DossierDB, dossier_id)
    if not dossier:
        raise HTTPException(404, "Dossier non trouve")

    if dossier.payment_captured:
        return {"status": "already_paid", "message": "Dossier deja paye"}

    # Montant en centimes
    amount_cents = int((dossier.montant_honoraires or 14.0) * 100)

    pro = await db.get(Professionnel, dossier.professionnel_id)

    from engine.payment.honoraires import HonorairesService
    service = HonorairesService()
    result = await service.create_checkout_session(
        dossier_id=dossier_id,
        professionnel_id=dossier.professionnel_id,
        amount_cents=amount_cents,
        stripe_customer_id=pro.stripe_customer_id if pro else None,
        success_url=f"https://app.autodocpro.fr/dossier/{dossier_id}?payment=success",
        cancel_url=f"https://app.autodocpro.fr/dossier/{dossier_id}?payment=cancelled",
    )

    return {
        "status": "checkout_created",
        "checkout_url": result["url"],
        "session_id": result["session_id"],
        "amount_cents": amount_cents,
    }


# ─── Double mandat 13757 (vendeur non habilité) ─────────────────────────────


@router.get("/{dossier_id}/mandats")
async def generate_mandats(dossier_id: UUID, db: AsyncSession = Depends(get_db)):
    """
    Génère les 2 mandats Cerfa 13757 pour un vendeur non habilité :
    - Mandat client → vendeur
    - Mandat client → agent habilité

    Retourne un ZIP avec les 2 PDFs.
    """
    import io
    import zipfile
    from fastapi.responses import StreamingResponse

    dossier = await db.get(DossierDB, dossier_id)
    if not dossier:
        raise HTTPException(404, "Dossier non trouve")

    pro = await db.get(Professionnel, dossier.professionnel_id)
    if not pro:
        raise HTTPException(404, "Professionnel non trouve")

    if pro.type_compte != "VENDEUR_NON_HABILITE":
        raise HTTPException(422, "Les mandats ne sont nécessaires que pour les vendeurs non habilités")

    if not pro.agent_nom:
        raise HTTPException(422, detail={
            "error": "agent_non_configure",
            "message": "Configurez d'abord votre agent habilité dans les paramètres.",
        })

    # Construire les données depuis le dossier
    from api.routers.documents import _build_dossier_dict
    dossier_dict = await _build_dossier_dict(db, dossier)

    # Extraire l'adresse client depuis les documents
    client_adresse = {}
    for doc in dossier_dict.get("documents", []):
        if doc.get("type") == "DOMICILE" and doc.get("extracted_data"):
            ext = doc["extracted_data"]
            adresse_raw = ext.get("adresse_ligne1", "") or ext.get("adresse", "")
            parts = adresse_raw.split(" ", 1) if adresse_raw else ["", ""]
            client_adresse = {
                "numero": parts[0] if len(parts) > 1 and parts[0].isdigit() else "",
                "nom_voie": parts[1] if len(parts) > 1 and parts[0].isdigit() else adresse_raw,
                "code_postal": ext.get("code_postal", ""),
                "commune": ext.get("ville", ""),
            }
            break

    client_nom = f"{dossier.client_nom or ''} {dossier.client_prenom or ''}".strip()

    from engine.cerfa.mandat_generator import generate_double_mandat
    mandat_vendeur, mandat_agent = generate_double_mandat(
        client_nom=client_nom,
        client_adresse=client_adresse,
        vendeur_nom=pro.nom_commerce or pro.raison_sociale or "",
        vendeur_siret=pro.siret or "",
        agent_nom=pro.agent_nom or "",
        agent_siret=pro.agent_siret or "",
        immatriculation=dossier.immatriculation or "",
        vin=dossier.vin or "",
        marque="",  # sera extrait du COC si dispo
        lieu=pro.ville or "",
    )

    # Sauvegarder dans le store
    store = get_document_store()
    ref = dossier.reference or ""
    await store.save(mandat_vendeur, f"{dossier_id}/mandats/Mandat_vendeur_13757_{ref}.pdf", "application/pdf")
    await store.save(mandat_agent, f"{dossier_id}/mandats/Mandat_agent_13757_{ref}.pdf", "application/pdf")

    # Retourner un ZIP avec les 2 mandats
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr(f"Mandat_vendeur_13757_{ref}.pdf", mandat_vendeur)
        zf.writestr(f"Mandat_agent_13757_{ref}.pdf", mandat_agent)
    buffer.seek(0)

    return StreamingResponse(
        buffer,
        media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="Mandats_13757_{ref}.zip"'},
    )


# ─── Transmission dossier → agent (vendeur non habilité) ────────────────────


@router.post("/{dossier_id}/transmettre-agent")
async def transmettre_agent(dossier_id: UUID, db: AsyncSession = Depends(get_db)):
    """
    Transmet le dossier complet à l'agent habilité du vendeur non habilité.
    Envoie un email à l'agent avec les infos du dossier.
    Marque le dossier comme transmis.
    """
    dossier = await db.get(DossierDB, dossier_id)
    if not dossier:
        raise HTTPException(404, "Dossier non trouve")

    pro = await db.get(Professionnel, dossier.professionnel_id)
    if not pro:
        raise HTTPException(404, "Professionnel non trouve")

    if pro.type_compte != "VENDEUR_NON_HABILITE":
        raise HTTPException(422, "La transmission n'est possible que pour les vendeurs non habilités")

    if not pro.agent_nom or not pro.agent_email:
        raise HTTPException(422, detail={
            "error": "agent_non_configure",
            "message": "Configurez l'email de votre agent habilité dans les paramètres.",
        })

    # Marquer comme transmis
    from sqlalchemy.orm.attributes import flag_modified
    metadata = dossier.metadata_ or {}
    metadata["transmis_agent"] = True
    metadata["transmis_agent_at"] = datetime.utcnow().isoformat()
    metadata["transmis_agent_nom"] = pro.agent_nom
    dossier.metadata_ = metadata
    flag_modified(dossier, "metadata_")
    await db.flush()

    # Notifier l'agent par email
    from notifications.email import send_email
    client_nom = f"{dossier.client_nom or ''} {dossier.client_prenom or ''}".strip()
    await send_email(pro.agent_email, "dossier_accepte", {
        "reference": dossier.reference or "",
        "diagnostic": dossier.diagnostic or "VERT",
        "tax_total": "—",
    })

    logger.info(f"[Transmission] Dossier {dossier_id} transmis à {pro.agent_nom} ({pro.agent_email})")

    return {
        "status": "transmis",
        "message": f"Dossier transmis à {pro.agent_nom}. Un email de notification a été envoyé.",
        "agent_nom": pro.agent_nom,
        "agent_email": pro.agent_email,
        "dossier_id": str(dossier_id),
    }


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
        "client_email": d.client_email,
        "tax_estimate": d.tax_estimate,
        "created_by_source": d.created_by_source,
        "created_at": d.created_at.isoformat() if d.created_at else None,
    }
