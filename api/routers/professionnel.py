"""
Router professionnel — paramétrage profil, cachet, signature, Kbis.

POST   /professionnel/profil           Créer/mettre à jour le profil
GET    /professionnel/profil           Consulter le profil
POST   /professionnel/profil/cachet    Uploader le cachet commercial
POST   /professionnel/profil/signature Uploader la signature
POST   /professionnel/profil/kbis      Uploader le Kbis (OCR + extraction SIREN)
"""
from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, UploadFile
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from api.models.base import get_db
from api.models.professionnel import Professionnel
from storage.document_store import get_document_store
from notifications.messages import PRO as MSG_PRO

router = APIRouter(prefix="/professionnel", tags=["professionnel"])


class ProfilSetupRequest(BaseModel):
    nom_commerce: str
    adresse: str
    telephone_commerce: str
    email_commerce: str | None = None
    assurance_flotte_vn: bool = False
    assurance_flotte_vo: bool = False
    demander_assurance_client_vn: bool = False
    demander_assurance_client_vo: bool = False


@router.post("/profil")
async def setup_profil(
    req: ProfilSetupRequest,
    pro_id: UUID = None,  # TODO: extraire du JWT
    db: AsyncSession = Depends(get_db),
):
    """
    Paramétrage initial du profil pro.

    Le pro renseigne : nom commerce, adresse, téléphone, assurance flotte.
    Cachet, signature et Kbis sont uploadés séparément.
    Ces infos sont intégrées dans le SMS envoyé au client.
    """
    # TODO: récupérer le pro depuis le JWT au lieu du paramètre
    pro = await db.get(Professionnel, pro_id) if pro_id else None
    if not pro:
        raise HTTPException(404, "Professionnel non trouvé")

    pro.nom_commerce = req.nom_commerce
    pro.adresse = req.adresse
    pro.telephone_commerce = req.telephone_commerce
    pro.email_commerce = req.email_commerce
    pro.assurance_flotte_vn = req.assurance_flotte_vn
    pro.assurance_flotte_vo = req.assurance_flotte_vo
    pro.demander_assurance_client_vn = req.demander_assurance_client_vn if not req.assurance_flotte_vn else False
    pro.demander_assurance_client_vo = req.demander_assurance_client_vo if not req.assurance_flotte_vo else False

    _update_setup_complete(pro)
    await db.flush()

    message = "Informations enregistrees."
    if pro.setup_complete:
        message = MSG_PRO["profil_pret"]

    return {"status": "ok", "message": message, "setup_complete": pro.setup_complete}


@router.get("/profil")
async def get_profil(
    pro_id: UUID = None,
    db: AsyncSession = Depends(get_db),
):
    pro = await db.get(Professionnel, pro_id) if pro_id else None
    if not pro:
        raise HTTPException(404, "Professionnel non trouvé")

    return {
        "nom_commerce": pro.nom_commerce,
        "adresse": pro.adresse,
        "telephone_commerce": pro.telephone_commerce,
        "email_commerce": pro.email_commerce,
        "siret": pro.siret,
        "raison_sociale": pro.raison_sociale,
        "cachet_uploaded": pro.cachet_path is not None,
        "signature_uploaded": pro.signature_path is not None,
        "kbis_uploaded": pro.kbis_path is not None,
        "assurance_flotte_vn": pro.assurance_flotte_vn,
        "assurance_flotte_vo": pro.assurance_flotte_vo,
        "demander_assurance_client_vn": pro.demander_assurance_client_vn,
        "demander_assurance_client_vo": pro.demander_assurance_client_vo,
        "setup_complete": pro.setup_complete,
    }


@router.post("/profil/cachet")
async def upload_cachet(
    file: UploadFile,
    pro_id: UUID = None,
    db: AsyncSession = Depends(get_db),
):
    pro = await db.get(Professionnel, pro_id) if pro_id else None
    if not pro:
        raise HTTPException(404, "Professionnel non trouvé")

    store = get_document_store()
    file_bytes = await file.read()
    path = f"profil/{pro.id}/cachet/{file.filename}"
    await store.save(file_bytes, path, file.content_type)

    pro.cachet_path = path
    _update_setup_complete(pro)
    await db.flush()

    return {"status": "ok", "message": "Cachet enregistre."}


@router.post("/profil/signature")
async def upload_signature(
    file: UploadFile,
    pro_id: UUID = None,
    db: AsyncSession = Depends(get_db),
):
    pro = await db.get(Professionnel, pro_id) if pro_id else None
    if not pro:
        raise HTTPException(404, "Professionnel non trouvé")

    store = get_document_store()
    file_bytes = await file.read()
    path = f"profil/{pro.id}/signature/{file.filename}"
    await store.save(file_bytes, path, file.content_type)

    pro.signature_path = path
    _update_setup_complete(pro)
    await db.flush()

    return {"status": "ok", "message": "Signature enregistree."}


@router.post("/profil/kbis")
async def upload_kbis(
    file: UploadFile,
    pro_id: UUID = None,
    db: AsyncSession = Depends(get_db),
):
    """
    Upload du Kbis — OCR + extraction SIREN/raison sociale.
    Auto-remplit les infos du profil.
    """
    pro = await db.get(Professionnel, pro_id) if pro_id else None
    if not pro:
        raise HTTPException(404, "Professionnel non trouvé")

    store = get_document_store()
    file_bytes = await file.read()
    path = f"profil/{pro.id}/kbis/{file.filename}"
    await store.save(file_bytes, path, file.content_type)

    pro.kbis_path = path

    # OCR + extraction (Tesseract → fallback Google DocAI)
    from engine.pipeline.realtime import _ocr_tesseract, _ocr_google_docai, classify_document, extract_data

    mime = file.content_type or "application/pdf"
    raw_text = ""
    ocr_confidence = 0.0

    try:
        tess = _ocr_tesseract(file_bytes, mime)
        raw_text = tess["text"]
        ocr_confidence = tess["confidence"]
    except Exception:
        pass

    # Fallback Google DocAI si Tesseract insuffisant
    if ocr_confidence < 0.50 or len(raw_text.strip()) < 50:
        try:
            goo = _ocr_google_docai(file_bytes, mime)
            if goo["confidence"] > ocr_confidence:
                raw_text = goo["text"]
                ocr_confidence = goo["confidence"]
        except Exception:
            pass

    # Extraire les infos du Kbis
    kbis_extracted = extract_data("KBIS", raw_text)

    # Verifier la date du Kbis (< 3 mois)
    kbis_warning = None
    from datetime import timedelta
    date_kbis = kbis_extracted.get("date_kbis") or kbis_extracted.get("date_document")
    if date_kbis:
        try:
            from datetime import datetime
            date_obj = datetime.strptime(date_kbis, "%d/%m/%Y")
            if (datetime.utcnow() - date_obj) > timedelta(days=90):
                kbis_warning = f"Kbis date du {date_kbis} (plus de 3 mois). Un Kbis recent est recommande."
        except (ValueError, TypeError):
            pass

    # Sauvegarder les infos extraites
    pro.kbis_extracted = kbis_extracted

    # Auto-remplir SIREN, raison sociale, adresse depuis le Kbis
    if kbis_extracted.get("siren"):
        pro.siret = kbis_extracted["siren"]
        pro.siren = kbis_extracted["siren"][:9] if len(kbis_extracted["siren"]) >= 9 else kbis_extracted["siren"]
    if kbis_extracted.get("raison_sociale"):
        pro.raison_sociale = kbis_extracted["raison_sociale"]
        if not pro.nom_commerce:
            pro.nom_commerce = kbis_extracted["raison_sociale"]
    if kbis_extracted.get("adresse"):
        pro.adresse = kbis_extracted["adresse"]

    _update_setup_complete(pro)
    await db.flush()

    result = {
        "status": "ok",
        "message": "Kbis enregistre — informations extraites automatiquement.",
        "ocr_confidence": ocr_confidence,
        "extracted": kbis_extracted,
    }
    if kbis_warning:
        result["warning"] = kbis_warning

    return result


def _update_setup_complete(pro: Professionnel) -> None:
    """Met à jour le flag setup_complete."""
    pro.setup_complete = bool(
        pro.nom_commerce
        and pro.adresse
        and pro.telephone_commerce
        and pro.cachet_path
        and pro.signature_path
        and pro.kbis_path
    )
