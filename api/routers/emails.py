"""
Router emails — drag & drop d'emails reçus du client.

POST   /emails/upload                 Upload un email entier (.eml ou .msg)
POST   /emails/upload-attachments     Upload directement plusieurs fichiers (PJ extraites)
POST   /emails/upload-to-dossier/{id} Upload des fichiers et les rattache à un dossier précis

Le flux principal est :
1. L'agent glisse un email sur l'interface
2. Le router parse l'email, extrait les pièces jointes
3. Pour chaque pièce, lance le pipeline OCR + classification + extraction
4. Cherche un dossier existant qui matche (détection hybride)
5. Retourne :
   - La liste des pièces extraites avec leurs données
   - Une suggestion de rattachement si un dossier existe
   - Sinon, propose la création d'un nouveau dossier
"""
from __future__ import annotations

import logging
import uuid
from io import BytesIO

from fastapi import APIRouter, Depends, HTTPException, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.datastructures import Headers
from starlette.datastructures import UploadFile as StarletteUploadFile

from api.dependencies import get_current_agent
from api.models.base import get_db
from api.models.dossier import DossierDB
from engine.dossier_matcher import find_matching_dossier, merge_hints
from engine.email_parser import EmailAttachment, ParsedEmail, extract_hints_from_email, parse_email_bytes

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/emails", tags=["emails"])


# ─── Configuration ──────────────────────────────────────────────────────────

MAX_EMAIL_SIZE = 50 * 1024 * 1024  # 50 MB (un email avec PJ peut être lourd)


# ─── Helpers internes ───────────────────────────────────────────────────────


def _attachment_to_uploadfile(att: EmailAttachment) -> StarletteUploadFile:
    """
    Convertit une EmailAttachment en UploadFile FastAPI pour pouvoir réutiliser
    l'endpoint /documents/{dossier_id}/upload existant.
    """
    headers = Headers({"content-type": att.mime_type})
    return StarletteUploadFile(
        filename=att.filename,
        file=BytesIO(att.content_bytes),
        headers=headers,
    )


async def _process_attachment_for_dossier(
    db: AsyncSession,
    dossier: DossierDB,
    att: EmailAttachment,
    parsed_email: ParsedEmail,
) -> dict:
    """
    Lance le pipeline OCR sur une pièce jointe et l'attache à un dossier.
    Retourne le résumé du document créé.
    """
    from api.routers.documents import upload_document

    upload_file = _attachment_to_uploadfile(att)
    return await upload_document(
        dossier_id=dossier.id,
        file=upload_file,
        doc_type=None,
        source_email_subject=parsed_email.subject,
        source_email_from=parsed_email.sender_email,
        db=db,
    )


def _extract_hints_from_attachment_results(results: list[dict]) -> dict:
    """
    Reconstruit des indices (VIN, immatriculation, nom) depuis les résultats
    d'extraction des pièces jointes.

    Permet d'enrichir le matching après OCR — par exemple un email sans VIN
    dans le sujet, mais dont une pièce jointe COC contient le VIN.
    """
    hints: dict = {}
    for r in results:
        ext = r.get("extracted") or {}
        if not ext:
            continue
        if not hints.get("vin") and ext.get("vin"):
            hints["vin"] = ext["vin"]
        if not hints.get("immatriculation") and ext.get("immatriculation"):
            hints["immatriculation"] = ext["immatriculation"]
        if not hints.get("client_nom"):
            for key in ("nom_naissance", "nom", "titulaire_nom"):
                if ext.get(key):
                    hints["client_nom"] = ext[key]
                    break
        if not hints.get("client_prenom"):
            for key in ("prenoms", "prenom"):
                if ext.get(key):
                    val = ext[key]
                    if isinstance(val, list):
                        val = " ".join(val)
                    hints["client_prenom"] = val
                    break
    return hints


# ─── Helper : drop direct d'un PDF/image hors email ────────────────────────


async def _upload_single_document(
    file,
    file_bytes: bytes,
    target_dossier_id: str | None,
    db: AsyncSession,
):
    """
    Cas où l'agent dépose directement un PDF/JPG/PNG (pas un .eml/.msg).
    On crée un dossier vide si nécessaire puis on déclenche le pipeline
    d'upload standard du router /documents pour bénéficier du multi-pages.
    """
    import uuid as _uuid
    import io
    from api.routers.documents import upload_document
    from fastapi import UploadFile

    # 1) Cible : si l'agent a explicitement choisi un dossier, l'utiliser.
    # Sinon : on attache au dossier PENDING le plus récent (un seul dossier
    # en construction à la fois — comportement attendu pour la session
    # d'agglomération CG + COC + CNI + permis + …). Si aucun, on crée.
    from sqlalchemy import select
    if target_dossier_id:
        dossier = await db.get(DossierDB, target_dossier_id)
        if not dossier:
            raise HTTPException(404, "Dossier cible non trouvé")
        dossier_id = dossier.id
    else:
        agent = await get_current_agent(db)
        # Chercher le dossier PENDING le plus récent de cet agent
        result = await db.execute(
            select(DossierDB)
            .where(DossierDB.professionnel_id == agent.id)
            .where(DossierDB.status == "PENDING")
            .order_by(DossierDB.created_at.desc())
            .limit(1)
        )
        existing = result.scalar_one_or_none()
        if existing:
            dossier_id = existing.id
        else:
            new = DossierDB(
                id=str(_uuid.uuid4()),
                reference=_make_reference(),
                type=None,
                status="PENDING",
                professionnel_id=agent.id,
            )
            db.add(new)
            await db.flush()
            dossier_id = new.id

    # 2) Reconstruire un UploadFile à partir des bytes pour appeler le pipeline.
    # content_type doit passer par headers (pas de setter direct sur UploadFile).
    from starlette.datastructures import Headers
    new_upload = UploadFile(
        filename=file.filename,
        file=io.BytesIO(file_bytes),
        headers=Headers({"content-type": file.content_type or "application/octet-stream"}),
    )

    upload_result = await upload_document(
        dossier_id=dossier_id,
        file=new_upload,
        doc_type=None,
        source_email_subject=None,
        source_email_from=None,
        db=db,
    )

    return {
        "email": None,
        "attachments_processed": [upload_result],
        "attachments_skipped": [],
        "suggested_dossier": {"id": dossier_id},
        "next_action": "attached" if target_dossier_id else "create_new",
        "dossier_id": dossier_id,
        "message": "Document ajouté au dossier.",
    }


def _make_reference() -> str:
    import random
    from datetime import datetime
    return f"CG-{datetime.utcnow().year}-{random.randint(10000, 99999)}"


# ─── Endpoint principal — drag & drop d'un email entier ────────────────────


@router.post("/upload")
async def upload_email(
    file: UploadFile,
    target_dossier_id: str | None = None,
    db: AsyncSession = Depends(get_db),
):
    """
    Upload un email entier (.eml ou .msg).

    Le système :
    1. Parse l'email et extrait les pièces jointes
    2. Si target_dossier_id est fourni → rattache directement à ce dossier
    3. Sinon, lance l'OCR sur les pièces et cherche un dossier candidat
    4. Si un dossier candidat est trouvé → propose le rattachement
    5. Sinon → suggère de créer un nouveau dossier

    L'agent garde le contrôle final via les boutons "Ajouter au dossier"
    ou "Créer un nouveau dossier" affichés dans l'interface.

    Args:
        file: l'email à parser (UploadFile)
        target_dossier_id: ID du dossier cible (si l'agent confirme un rattachement)

    Returns:
        {
            "email": {sender, subject, date, format, body_excerpt},
            "attachments_processed": [...],  # résultats OCR + extraction
            "attachments_skipped": [...],    # pièces non traitables (HTML, signatures)
            "suggested_dossier": {...} | None,
            "next_action": "create_new" | "attach_to_existing" | "attached"
        }
    """
    # Vérifier l'agent (créé d'office au démarrage, profil désormais optionnel)
    agent = await get_current_agent(db)
    if not agent:
        raise HTTPException(404, "Aucun agent configuré sur cette installation")

    # Lire le fichier
    file_bytes = await file.read()
    if not file_bytes:
        raise HTTPException(422, "Email vide")
    if len(file_bytes) > MAX_EMAIL_SIZE:
        raise HTTPException(422, f"Email trop volumineux (max {MAX_EMAIL_SIZE // (1024*1024)} MB)")

    # Si l'utilisateur dépose directement un PDF/image (pas un email), on
    # bascule sur le flux "document direct" : création d'un dossier vide +
    # upload du fichier comme document unique.
    fname_lower = (file.filename or "").lower()
    is_email_file = fname_lower.endswith((".eml", ".msg")) or (
        file.content_type or ""
    ) in ("message/rfc822", "application/vnd.ms-outlook")
    if not is_email_file:
        return await _upload_single_document(file, file_bytes, target_dossier_id, db)

    # Parser l'email
    try:
        parsed = parse_email_bytes(file_bytes, filename=file.filename or "")
    except Exception as e:
        logger.error(f"[emails] parse échoué : {e}")
        raise HTTPException(422, detail={
            "error": "email_parse_failed",
            "message": f"Impossible de lire ce fichier email : {e}",
        })

    # Liste des pièces traitables et ignorées
    processable = parsed.processable_attachments
    skipped = [
        {"filename": a.filename, "mime_type": a.mime_type, "reason": "non_processable"}
        for a in parsed.attachments
        if not a.is_processable
    ]

    if not processable and not target_dossier_id:
        return {
            "email": _email_summary(parsed),
            "attachments_processed": [],
            "attachments_skipped": skipped,
            "suggested_dossier": None,
            "next_action": "no_attachments",
            "message": "Cet email ne contient aucune pièce jointe traitable (PDF, JPG, PNG).",
        }

    # ─── Cas 1 : l'agent a déjà choisi un dossier cible ────────────────────
    if target_dossier_id:
        dossier = await db.get(DossierDB, target_dossier_id)
        if not dossier:
            raise HTTPException(404, "Dossier cible non trouvé")

        results = []
        for att in processable:
            try:
                r = await _process_attachment_for_dossier(db, dossier, att, parsed)
                results.append(r)
            except Exception as e:
                logger.warning(f"[emails] pièce {att.filename} échouée : {e}")
                results.append({"filename": att.filename, "error": str(e)})

        await db.flush()
        return {
            "email": _email_summary(parsed),
            "attachments_processed": results,
            "attachments_skipped": skipped,
            "dossier_id": dossier.id,
            "next_action": "attached",
            "message": f"{len(results)} pièce(s) ajoutée(s) au dossier {dossier.reference}.",
        }

    # ─── Cas 2 : pas de dossier cible — créer un dossier temporaire et matcher ──
    # On crée un dossier temporaire pour stocker les pièces, puis on cherche
    # un dossier candidat. Si l'agent valide le rattachement, on déplace les
    # pièces vers le dossier existant et on supprime le temporaire.

    # Pour simplifier, on crée d'abord un dossier "draft" et on garde son ID
    from datetime import datetime
    import random
    year = datetime.utcnow().year
    seq = random.randint(10000, 99999)
    draft_dossier = DossierDB(
        id=str(uuid.uuid4()),
        reference=f"CG-{year}-{seq}",
        type=None,
        status="PENDING",
        professionnel_id=agent.id,
        client_email=parsed.sender_email or None,
        metadata_={"draft_from_email": True, "email_subject": parsed.subject},
    )
    db.add(draft_dossier)
    await db.flush()

    # Traiter les pièces jointes vers le dossier draft
    results = []
    for att in processable:
        try:
            r = await _process_attachment_for_dossier(db, draft_dossier, att, parsed)
            results.append(r)
        except Exception as e:
            logger.warning(f"[emails] pièce {att.filename} échouée : {e}")
            results.append({"filename": att.filename, "error": str(e)})

    # Recharger le dossier draft pour récupérer les champs auto-extraits (vin, etc.)
    await db.refresh(draft_dossier)

    # Construire les indices à partir de l'email + des résultats d'OCR
    email_hints = extract_hints_from_email(parsed)
    ocr_hints = _extract_hints_from_attachment_results(results)
    draft_hints = {
        "vin": draft_dossier.vin,
        "immatriculation": draft_dossier.immatriculation,
        "client_nom": draft_dossier.client_nom,
        "client_prenom": draft_dossier.client_prenom,
        "client_email": draft_dossier.client_email,
        "client_telephone": draft_dossier.client_telephone,
    }
    hints = merge_hints(email_hints, ocr_hints, draft_hints)

    # Chercher un dossier candidat (en excluant le draft lui-même)
    candidate = await find_matching_dossier(db, hints)
    if candidate and candidate.dossier_id == draft_dossier.id:
        candidate = None  # Ignorer le draft que l'on vient de créer

    if candidate:
        return {
            "email": _email_summary(parsed),
            "draft_dossier_id": draft_dossier.id,
            "attachments_processed": results,
            "attachments_skipped": skipped,
            "suggested_dossier": {
                "id": candidate.dossier_id,
                "reference": candidate.reference,
                "client_nom": candidate.client_nom,
                "client_prenom": candidate.client_prenom,
                "vin": candidate.vin,
                "immatriculation": candidate.immatriculation,
                "type": candidate.type,
                "status": candidate.status,
                "confidence": candidate.confidence,
                "match_reason": candidate.match_reason,
                "created_at": candidate.created_at.isoformat() if candidate.created_at else None,
            },
            "next_action": "confirm_attach_or_create",
            "message": (
                f"Ce document semble appartenir au dossier {candidate.reference} "
                f"({candidate.client_nom or '?'} {candidate.client_prenom or ''}). "
                f"Confirmez l'ajout à ce dossier ou créez un nouveau dossier."
            ),
        }

    # Pas de candidat — on garde le dossier draft comme nouveau dossier officiel
    return {
        "email": _email_summary(parsed),
        "dossier_id": draft_dossier.id,
        "dossier_reference": draft_dossier.reference,
        "attachments_processed": results,
        "attachments_skipped": skipped,
        "suggested_dossier": None,
        "next_action": "created_new",
        "message": (
            f"Nouveau dossier {draft_dossier.reference} créé avec "
            f"{len(results)} pièce(s) jointe(s) traitée(s)."
        ),
    }


# ─── Endpoint utilitaire — preview parsing sans OCR ────────────────────────


@router.post("/preview")
async def preview_email(file: UploadFile):
    """
    Parse un email sans lancer l'OCR ni créer de dossier.
    Permet à l'interface de prévisualiser le contenu avant traitement.
    """
    file_bytes = await file.read()
    if not file_bytes:
        raise HTTPException(422, "Email vide")

    try:
        parsed = parse_email_bytes(file_bytes, filename=file.filename or "")
    except Exception as e:
        raise HTTPException(422, f"Impossible de lire l'email : {e}")

    return {
        "email": _email_summary(parsed),
        "attachments": [
            {
                "filename": a.filename,
                "mime_type": a.mime_type,
                "size_bytes": a.size_bytes,
                "is_processable": a.is_processable,
            }
            for a in parsed.attachments
        ],
        "hints": extract_hints_from_email(parsed),
    }


# ─── Helpers ────────────────────────────────────────────────────────────────


def _email_summary(parsed: ParsedEmail) -> dict:
    """Résumé court d'un email parsé pour l'interface."""
    body = parsed.body_text or _strip_html(parsed.body_html)
    return {
        "sender_name": parsed.sender_name,
        "sender_email": parsed.sender_email,
        "subject": parsed.subject,
        "date": parsed.date,
        "format": parsed.format,
        "body_excerpt": (body[:500] + "...") if body and len(body) > 500 else body,
        "attachments_count": len(parsed.attachments),
        "processable_count": len(parsed.processable_attachments),
    }


def _strip_html(html: str) -> str:
    """Nettoyage HTML très basique pour l'aperçu (pas besoin de BeautifulSoup)."""
    if not html:
        return ""
    import re
    text = re.sub(r"<[^>]+>", " ", html)
    text = re.sub(r"\s+", " ", text)
    return text.strip()
