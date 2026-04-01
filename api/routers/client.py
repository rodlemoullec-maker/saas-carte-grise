"""
Router client — page d'upload accessible via le lien securise SMS.

Utilise le moteur realtime (engine/pipeline/realtime.py) pour :
- Checklist dynamique des documents client
- Verification reglementaire (permis, age, etc.)
- Croisements inter-documents
- Messages de session (premiere visite / retour)
"""
from __future__ import annotations

from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm.attributes import flag_modified

from api.models.base import get_db
from notifications.messages import CLIENT as MSG_CLIENT
from api.models.document import DocumentDB
from api.models.dossier import DossierDB
from api.models.professionnel import Professionnel
from api.routers.documents import _build_dossier_dict
from engine.pipeline.realtime import (
    _check_client_docs,
    _get_client_docs_attendus,
    _auto_extract_client_fields,
    _build_session_message,
)

router = APIRouter(prefix="/client", tags=["client"])


class ChoixCPIRequest(BaseModel):
    mode: str  # "email" ou "main_propre"
    email: str | None = None


@router.get("/{token}")
async def get_client_page(token: str, db: AsyncSession = Depends(get_db)):
    """Page d'upload client — moteur realtime connecte."""
    dossier = await _get_dossier_by_token(db, token)
    pro = await db.get(Professionnel, dossier.professionnel_id)
    nom_commerce = pro.nom_commerce if pro else "votre vendeur"
    tel_commerce = pro.telephone_commerce if pro else ""
    metadata = dossier.metadata_ or {}

    # Lien desactive apres finalisation
    if dossier.status in ("CERFA_GENERE", "SOUMIS"):
        cpi_mode = metadata.get("cpi_mode", "main_propre")
        if cpi_mode == "email":
            cpi_msg = f"{nom_commerce} vous enverra votre CPI par email une fois qu'il aura finalise le dossier aupres du SIV."
        else:
            cpi_msg = f"{nom_commerce} vous contactera directement une fois qu'il aura finalise le dossier aupres du SIV."

        return {
            "status": "termine",
            "message": MSG_CLIENT["dossier_termine"].format(nom_commerce=nom_commerce),
            "prochaines_etapes": [
                f"{nom_commerce} va soumettre votre dossier aupres du SIV.",
                f"{cpi_msg} Ce document vous permettra de circuler pendant 1 mois.",
                "Votre carte grise definitive sera envoyee par courrier securise a l'adresse figurant sur votre justificatif de domicile, sous 3 a 7 jours ouvrables.",
            ],
            "contact": f"Pour toute question, contactez {nom_commerce}" + (f" au {tel_commerce}" if tel_commerce else "") + ".",
        }

    # Construire le dossier dict pour le moteur realtime
    dossier_dict = await _build_dossier_dict(db, dossier)

    # Checklist et docs attendus dynamiques
    checklist = _check_client_docs(dossier_dict)
    docs_attendus = _get_client_docs_attendus(dossier_dict)
    session = _build_session_message(dossier_dict, checklist)

    return {
        "dossier_id": str(dossier.id),
        "reference": dossier.reference,
        "type": dossier.type,
        "commerce": {
            "nom": pro.nom_commerce if pro else None,
            "adresse": pro.adresse if pro else None,
            "telephone": tel_commerce,
        },
        "rgpd": {
            "responsable": "AutoDoc Pro",
            "finalite": f"Traitement de votre demande de carte grise initiee par {nom_commerce}.",
            "base_legale": "Consentement (article 6.1.a RGPD)",
            "destinataires": (
                f"Vos documents sont transmis a {nom_commerce} et traites par AutoDoc Pro. "
                "Le traitement automatise des documents (lecture et extraction des informations) "
                "est realise par Google Document AI (Google LLC, USA) et Anthropic (Claude, USA) "
                "dans le cadre de clauses contractuelles types conformes au RGPD."
            ),
            "sous_traitants": [
                {"nom": "Google LLC", "service": "Google Document AI", "role": "Lecture optique des documents (OCR)", "pays": "USA", "garanties": "Clauses contractuelles types (CCT)"},
                {"nom": "Anthropic", "service": "Claude", "role": "Extraction et structuration des donnees des documents", "pays": "USA", "garanties": "Clauses contractuelles types (CCT)"},
            ],
            "conservation": (
                "Vos documents sont traites en temps reel et ne sont pas conserves par nos sous-traitants "
                "(Google, Anthropic) au-dela du traitement. Anthropic ne conserve pas les donnees envoyees via l'API "
                "et ne les utilise pas pour entrainer ses modeles. "
                "AutoDoc Pro conserve vos documents uniquement le temps de la demarche puis les supprime automatiquement."
            ),
            "transfert_hors_ue": (
                "Vos donnees sont transferees vers les Etats-Unis dans le cadre du traitement par Google Document AI "
                "et Anthropic (Claude). Ces transferts sont encadres par des clauses contractuelles types (CCT) "
                "conformement a l'article 46 du RGPD."
            ),
            "droits": "Acces, rectification, suppression, portabilite, opposition — contact : rgpd@cartegrisepro.fr",
            "contact_dpo": "rgpd@cartegrisepro.fr",
            "politique_complete": "cartegrisepro.fr/confidentialite",
        },
        "consentement": {
            "requis": True,
            "accepte": metadata.get("client_rgpd_consent", False),
            "texte": (
                f"J'accepte que mes documents d'identite soient traites par AutoDoc Pro "
                f"et transmis a {nom_commerce} dans le seul but de realiser ma demande de carte grise. "
                "Mes documents sont lus par Google Document AI et analyses par Claude (Anthropic) "
                "pour en extraire les informations. Ces sous-traitants sont bases aux Etats-Unis "
                "et ne conservent pas mes donnees. "
                "J'ai pris connaissance de la politique de confidentialite."
            ),
        },
        "choix_cpi": {
            "requis": True,
            "choisi": metadata.get("cpi_mode") is not None,
            "mode": metadata.get("cpi_mode"),
            "email": metadata.get("cpi_email"),
            "options": [
                {"id": "main_propre", "label": f"Je recupererai mon CPI en main propre aupres de {nom_commerce}"},
                {"id": "email", "label": "Je souhaite recevoir mon CPI par email", "champ_email_requis": True},
            ],
        },
        "cession": {
            "signature_requise": bool(
                metadata.get("pas_de_certificat_cession")
                and (dossier.type or "").upper() in ("VO", "OCCASION")
            ),
            "signee": metadata.get("cession_signee_client", False),
            "telechargee": metadata.get("cession_client_telechargee", False),
        },
        "mentions_legales": {
            "authenticite": "En deposant vos documents, vous certifiez qu'ils sont authentiques (art. 441-1 Code penal).",
            "exactitude": "Vous certifiez que les informations contenues dans vos documents sont exactes et a jour.",
            "role_service": "AutoDoc Pro est un outil d'aide, pas un conseiller juridique ni un substitut de l'administration.",
            "responsabilite": f"La soumission du dossier est effectuee par {nom_commerce} sous sa responsabilite.",
            "conservation": "Vos documents sont supprimes automatiquement une fois le dossier finalise.",
        },
        "intro_checklist": MSG_CLIENT["intro_checklist"],
        "documents_attendus": docs_attendus,
        "checklist": checklist,
        "session": session,
    }


@router.post("/{token}/consent")
async def accept_consent(token: str, db: AsyncSession = Depends(get_db)):
    dossier = await _get_dossier_by_token(db, token)
    metadata = dossier.metadata_ or {}
    metadata["client_rgpd_consent"] = True
    metadata["client_rgpd_consent_at"] = datetime.utcnow().isoformat()
    dossier.metadata_ = metadata
    flag_modified(dossier, 'metadata_')
    await db.flush()
    return {"status": "ok", "message": MSG_CLIENT["consentement_ok"]}


@router.post("/{token}/choix-cpi")
async def choix_cpi(token: str, req: ChoixCPIRequest, db: AsyncSession = Depends(get_db)):
    dossier = await _get_dossier_by_token(db, token)
    if req.mode not in ("email", "main_propre"):
        raise HTTPException(422, "Mode invalide.")
    if req.mode == "email" and (not req.email or "@" not in req.email):
        raise HTTPException(422, "Adresse email requise.")

    metadata = dossier.metadata_ or {}
    metadata["cpi_mode"] = req.mode
    if req.email:
        metadata["cpi_email"] = req.email
    dossier.metadata_ = metadata
    flag_modified(dossier, 'metadata_')
    await db.flush()

    pro = await db.get(Professionnel, dossier.professionnel_id)
    nom_commerce = pro.nom_commerce if pro else "votre vendeur"
    if req.mode == "email":
        msg = MSG_CLIENT["cpi_email"].format(email=req.email)
    else:
        msg = MSG_CLIENT["cpi_main_propre"].format(nom_commerce=nom_commerce)
    return {"status": "ok", "message": msg}


@router.post("/{token}/signer-cession")
async def signer_cession(token: str, db: AsyncSession = Depends(get_db)):
    """Le client signe le certificat de cession (VO, si pas de cession deposee par le pro)."""
    dossier = await _get_dossier_by_token(db, token)
    metadata = dossier.metadata_ or {}

    if not metadata.get("pas_de_certificat_cession"):
        raise HTTPException(422, "Le certificat de cession a ete depose par le vendeur — pas de signature requise.")

    metadata["cession_signee_client"] = True
    metadata["cession_signee_client_at"] = datetime.utcnow().isoformat()
    metadata["cession_client_telechargee"] = False
    dossier.metadata_ = metadata
    flag_modified(dossier, 'metadata_')
    await db.flush()

    return {
        "status": "cession_signee",
        "message": MSG_CLIENT["cession_signee"],
        "telechargement_obligatoire": True,
        "telechargement_url": f"/client/{token}/telecharger-cession",
        "upload_bloque": True,
    }


@router.get("/{token}/telecharger-cession")
async def telecharger_cession(token: str, db: AsyncSession = Depends(get_db)):
    """Le client telecharge son exemplaire du certificat de cession signe."""
    dossier = await _get_dossier_by_token(db, token)
    metadata = dossier.metadata_ or {}

    if not metadata.get("cession_signee_client"):
        raise HTTPException(422, "Le certificat de cession n'a pas encore ete signe.")

    metadata["cession_client_telechargee"] = True
    metadata["cession_client_telechargee_at"] = datetime.utcnow().isoformat()
    dossier.metadata_ = metadata
    flag_modified(dossier, 'metadata_')
    await db.flush()

    return {
        "status": "ok",
        "message": MSG_CLIENT["cession_telechargee"],
        "upload_debloque": True,
    }


@router.post("/{token}/confirmer-envoi")
async def confirmer_envoi(token: str, db: AsyncSession = Depends(get_db)):
    dossier = await _get_dossier_by_token(db, token)

    # Verifier checklist complete
    dossier_dict = await _build_dossier_dict(db, dossier)
    checklist = _check_client_docs(dossier_dict)
    if not checklist.get("ready_for_diagnostic"):
        raise HTTPException(422, detail={
            "error": "docs_incomplets",
            "message": "Tous les documents ne sont pas encore deposes ou valides.",
            "checklist": checklist,
        })

    metadata = dossier.metadata_ or {}
    metadata["client_docs_envoyes"] = True
    metadata["client_docs_envoyes_at"] = datetime.utcnow().isoformat()
    dossier.metadata_ = metadata
    flag_modified(dossier, 'metadata_')
    await db.flush()

    pro = await db.get(Professionnel, dossier.professionnel_id)
    nom_commerce = pro.nom_commerce if pro else "votre vendeur"
    tel_commerce = pro.telephone_commerce if pro else ""

    cpi_mode = metadata.get("cpi_mode", "main_propre")
    if cpi_mode == "email":
        cpi_msg = f"{nom_commerce} vous enverra votre CPI par email une fois qu'il aura finalise le dossier aupres du SIV."
    else:
        cpi_msg = f"{nom_commerce} vous contactera directement une fois qu'il aura finalise le dossier aupres du SIV."

    return {
        "status": "envoye",
        "message": MSG_CLIENT["envoi_confirme"].format(nom_commerce=nom_commerce),
        "prochaines_etapes": [
            f"{nom_commerce} va verifier votre dossier et soumettre la demande aupres du SIV.",
            f"{cpi_msg} Ce document vous permettra de circuler pendant 1 mois.",
            "Votre carte grise definitive sera envoyee par courrier securise a l'adresse figurant sur votre justificatif de domicile, sous 3 a 7 jours ouvrables.",
        ],
        "contact": f"Pour toute question, contactez {nom_commerce}" + (f" au {tel_commerce}" if tel_commerce else "") + ".",
    }


@router.delete("/{token}/document/{doc_type}")
async def supprimer_document(token: str, doc_type: str, db: AsyncSession = Depends(get_db)):
    dossier = await _get_dossier_by_token(db, token)

    metadata = dossier.metadata_ or {}
    if metadata.get("client_docs_envoyes"):
        raise HTTPException(422, detail={
            "error": "docs_deja_envoyes",
            "message": MSG_CLIENT["docs_deja_envoyes"],
        })

    # Supprimer le document de la BDD
    result = await db.execute(
        select(DocumentDB).where(
            DocumentDB.dossier_id == dossier.id,
            DocumentDB.source == "client",
            DocumentDB.type == doc_type.upper(),
        )
    )
    doc = result.scalar_one_or_none()
    if not doc:
        raise HTTPException(404, f"Document de type '{doc_type}' non trouve.")

    await db.delete(doc)
    await db.flush()

    # Recalculer la checklist
    dossier_dict = await _build_dossier_dict(db, dossier)

    # Reset flags si besoin (#52-53 — aligne avec demo_server)
    if doc_type.upper() == "KBIS":
        # Ne PAS reset is_personne_morale — c'est le client qui l'a coche
        # Le Kbis sera re-demande dans la checklist
        pass
    if doc_type.upper() in ("CNI", "PASSEPORT"):
        metadata = dossier.metadata_ or {}
        metadata.pop("client_sexe", None)
        dossier.metadata_ = metadata

    await db.flush()

    return {
        "status": "ok",
        "message": MSG_CLIENT["doc_supprime"].format(doc_type=doc_type),
        "checklist": _check_client_docs(dossier_dict),
        "documents_attendus": _get_client_docs_attendus(dossier_dict),
    }


# ─── Helpers ─────────────────────────────────────────────────────────────────

async def _get_dossier_by_token(db: AsyncSession, token: str) -> DossierDB:
    result = await db.execute(
        select(DossierDB).where(DossierDB.client_link_token == token)
    )
    dossier = result.scalar_one_or_none()
    if not dossier:
        raise HTTPException(404, "Lien invalide ou expire")
    return dossier
