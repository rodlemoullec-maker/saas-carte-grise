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
                pro.type_compte != "AGENT_HABILITE"  # L'agent ne génère pas de cession
                and metadata.get("pas_de_certificat_cession")
                and (dossier.type or "").upper() in ("VO", "OCCASION")
            ),
            "signee": metadata.get("cession_signee_client", False),
            "telechargee": metadata.get("cession_client_telechargee", False),
        },
        "mandats": {
            "signature_requise": pro.type_compte == "VENDEUR_NON_HABILITE",
            "signes": metadata.get("mandats_signes_client", False),
            "vendeur_nom": pro.nom_commerce or "",
            "agent_nom": pro.agent_nom or "",
        },
        "mentions_legales": {
            "authenticite": "En deposant vos documents, vous certifiez qu'ils sont authentiques (art. 441-1 Code penal).",
            "exactitude": "Vous certifiez que les informations contenues dans vos documents sont exactes et a jour.",
            "role_service": "AutoDoc Pro est un outil d'aide, pas un conseiller juridique ni un substitut de l'administration.",
            "responsabilite": f"La soumission du dossier est effectuee par {nom_commerce} sous sa responsabilite." if pro.type_compte != "AGENT_HABILITE"
                else f"La soumission du dossier est effectuee par {nom_commerce} en tant qu'intermediaire habilite.",
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


# ─── Signature mandats 13757 par OTP SMS ────────────────────────────────────


@router.post("/{token}/demander-otp-mandat")
async def demander_otp_mandat(token: str, db: AsyncSession = Depends(get_db)):
    """
    Envoie un code OTP par SMS au client pour signer les mandats 13757.
    Disponible uniquement pour les dossiers de vendeurs non habilités.
    """
    import secrets

    dossier = await _get_dossier_by_token(db, token)
    pro = await db.get(Professionnel, dossier.professionnel_id)

    if not pro or pro.type_compte != "VENDEUR_NON_HABILITE":
        raise HTTPException(422, "La signature de mandats n'est requise que pour les vendeurs non habilités.")

    metadata = dossier.metadata_ or {}
    if metadata.get("mandats_signes_client"):
        return {"status": "deja_signe", "message": "Les mandats ont déjà été signés."}

    # Générer le code OTP (6 chiffres)
    code = str(secrets.randbelow(900000) + 100000)
    metadata["mandat_otp_code"] = code
    metadata["mandat_otp_at"] = datetime.utcnow().isoformat()
    dossier.metadata_ = metadata
    flag_modified(dossier, "metadata_")
    await db.flush()

    # Envoyer le SMS
    from notifications.sms import send_sms, build_sms_otp
    sms_text = build_sms_otp(code)
    await send_sms(dossier.client_telephone, sms_text)

    return {
        "status": "otp_envoye",
        "message": MSG_CLIENT["cession_otp"].format(telephone=dossier.client_telephone),
        "telephone_masque": dossier.client_telephone[:4] + "••••" + dossier.client_telephone[-2:] if dossier.client_telephone else "",
    }


class SignerMandatsRequest(BaseModel):
    code: str


@router.post("/{token}/signer-mandats")
async def signer_mandats(token: str, req: SignerMandatsRequest, db: AsyncSession = Depends(get_db)):
    """
    Valide le code OTP et signe numériquement les 2 mandats 13757.
    Génère les PDFs avec mention de signature et les stocke.
    """
    dossier = await _get_dossier_by_token(db, token)
    pro = await db.get(Professionnel, dossier.professionnel_id)

    if not pro or pro.type_compte != "VENDEUR_NON_HABILITE":
        raise HTTPException(422, "Signature mandats non applicable.")

    metadata = dossier.metadata_ or {}

    if metadata.get("mandats_signes_client"):
        return {"status": "deja_signe", "message": "Les mandats ont déjà été signés."}

    # Vérifier le code OTP
    stored_code = metadata.get("mandat_otp_code")
    if not stored_code:
        raise HTTPException(422, "Aucun code OTP demandé. Cliquez d'abord sur 'Signer les mandats'.")

    # Expiration : 10 minutes
    otp_at = metadata.get("mandat_otp_at", "")
    if otp_at:
        from datetime import timedelta
        otp_time = datetime.fromisoformat(otp_at)
        if (datetime.utcnow() - otp_time) > timedelta(minutes=10):
            raise HTTPException(422, "Code expiré. Demandez un nouveau code.")

    if req.code != stored_code:
        raise HTTPException(422, "Code incorrect.")

    # Générer les mandats PDF
    from api.routers.documents import _build_dossier_dict
    dossier_dict = await _build_dossier_dict(db, dossier)

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
        marque="",
        lieu=pro.ville or "",
    )

    # Stocker les mandats signés
    from storage.document_store import get_document_store
    store = get_document_store()
    ref = dossier.reference or ""
    await store.save(mandat_vendeur, f"{dossier.id}/mandats/Mandat_vendeur_13757_{ref}_signe.pdf", "application/pdf")
    await store.save(mandat_agent, f"{dossier.id}/mandats/Mandat_agent_13757_{ref}_signe.pdf", "application/pdf")

    # Marquer comme signé
    metadata["mandats_signes_client"] = True
    metadata["mandats_signes_at"] = datetime.utcnow().isoformat()
    metadata["mandats_signes_par"] = client_nom
    metadata.pop("mandat_otp_code", None)
    dossier.metadata_ = metadata
    flag_modified(dossier, "metadata_")
    await db.flush()

    return {
        "status": "mandats_signes",
        "message": "Les deux mandats ont été signés avec succès.",
        "mandats": [
            {"type": "client_vendeur", "label": f"Mandat client → {pro.nom_commerce or 'vendeur'}"},
            {"type": "client_agent", "label": f"Mandat client → {pro.agent_nom or 'agent'}"},
        ],
    }


# ─── Signature cession ─────────────────────────────────────────────────────


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

    # Notifier le pro par email
    if pro and pro.email_commerce:
        from notifications.email import send_email
        docs_list = "\n".join(
            f"- {d.get('type', '?')} ({d.get('status', '?')})"
            for d in dossier_dict.get("documents_client", [])
        )
        await send_email(pro.email_commerce, "client_a_uploade", {
            "reference": dossier.reference or "",
            "client_nom": f"{dossier.client_nom or ''} {dossier.client_prenom or ''}".strip(),
            "documents_list": docs_list or "—",
        })

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
