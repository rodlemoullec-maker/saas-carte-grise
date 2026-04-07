"""
Router documents — version locale d'Imatra.

POST   /documents/{dossier_id}/upload     Uploader un document (depuis fichier local)
GET    /documents/{document_id}           Détail + résultat d'extraction

L'upload appelle le pipeline OCR local (PaddleOCR via la factory)
puis classifie et extrait les données du document.

Le drag & drop d'emails (Phase 4) sera ajouté dans un router séparé
qui appellera ce même endpoint en boucle pour chaque pièce jointe.
"""
from __future__ import annotations

import logging
import uuid

from fastapi import APIRouter, Depends, HTTPException, UploadFile
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.models.base import get_db
from api.models.document import DocumentDB
from api.models.dossier import DossierDB
from storage.document_store import get_document_store

# Pipeline métier
from engine.pipeline.realtime import (
    classify_document,
    extract_data,
    _auto_detect_dossier_type,
    _auto_extract_dossier_fields,
    _auto_extract_client_fields,
    _check_pro_docs,
    _check_client_docs,
    set_profil_pro,
)

logger = logging.getLogger(__name__)

router = APIRouter()


# ─── Configuration ──────────────────────────────────────────────────────────

ALLOWED_MIME_TYPES = {
    "application/pdf",
    "image/jpeg",
    "image/png",
    "image/tiff",
    "image/webp",
}
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB

OCR_SEUIL_ILLISIBLE = 0.40
OCR_SEUIL_AVERTISSEMENT = 0.70


# ─── Endpoint upload ────────────────────────────────────────────────────────


@router.post("/{dossier_id}/upload", status_code=201)
async def upload_document(
    dossier_id: str,
    file: UploadFile,
    doc_type: str | None = None,
    source_email_subject: str | None = None,
    source_email_from: str | None = None,
    db: AsyncSession = Depends(get_db),
):
    """
    Upload un document — OCR + classification + extraction en local.

    L'agent uploade un fichier (depuis son disque ou extrait d'un email).
    Le pipeline tourne intégralement en local via PaddleOCR.
    """
    dossier = await db.get(DossierDB, dossier_id)
    if not dossier:
        raise HTTPException(status_code=404, detail="Dossier non trouvé")

    # Filtrer les fichiers système
    fname = file.filename or ""
    if fname.startswith(".") or fname in (".DS_Store", "Thumbs.db", "desktop.ini"):
        raise HTTPException(status_code=422, detail=f"Fichier système ignoré : {fname}")

    if file.content_type not in ALLOWED_MIME_TYPES:
        raise HTTPException(
            status_code=422,
            detail=f"Type de fichier non supporté : {file.content_type}",
        )

    file_bytes = await file.read()
    if len(file_bytes) > MAX_FILE_SIZE:
        raise HTTPException(status_code=422, detail="Fichier trop volumineux (max 10 MB)")
    if len(file_bytes) == 0:
        raise HTTPException(status_code=422, detail="Fichier vide")

    # Stocker le fichier (chiffré local)
    store = get_document_store()
    sha256 = store.compute_sha256(file_bytes)
    doc_id = str(uuid.uuid4())
    storage_path = f"{dossier_id}/{doc_id}/{file.filename}"
    await store.save(file_bytes, storage_path, file.content_type)

    # Créer en BDD
    document = DocumentDB(
        id=doc_id,
        dossier_id=dossier_id,
        type="PENDING",
        status="PENDING",
        storage_path=storage_path,
        original_filename=file.filename or "unknown",
        mime_type=file.content_type,
        file_size_bytes=len(file_bytes),
        sha256=sha256,
        source_email_subject=source_email_subject,
        source_email_from=source_email_from,
    )
    db.add(document)
    await db.flush()

    # ════════════════════════════════════════════════════════════════════
    # PIPELINE LOCAL : PaddleOCR → classification → extraction
    # ════════════════════════════════════════════════════════════════════
    raw_text = ""
    ocr_confidence = 0.0
    ocr_provider_used = "none"

    try:
        from integrations.ocr_providers import get_ocr_provider
        from config.settings import get_settings
        provider = get_ocr_provider(get_settings().ocr_provider)
        ocr_result = await provider.process_document(file_bytes, file.content_type or "")
        raw_text = ocr_result.full_text
        ocr_confidence = ocr_result.average_confidence
        ocr_provider_used = ocr_result.provider
        logger.info(
            f"[OCR] {ocr_provider_used}: {ocr_confidence:.0%}, {len(raw_text)} chars"
        )
    except Exception as e:
        logger.error(f"[OCR] échec : {e}")

    # Qualité
    if ocr_confidence < OCR_SEUIL_ILLISIBLE:
        quality_status = "illisible"
        quality_message = "Document illisible. Re-scannez ou photographiez à nouveau."
    elif ocr_confidence < OCR_SEUIL_AVERTISSEMENT:
        quality_status = "avertissement"
        quality_message = "Lecture partielle — vérifiez les champs extraits."
    else:
        quality_status = "ok"
        quality_message = "Document bien reçu et lisible."

    # Classification
    detected_type = "PENDING"
    cls_confidence = 0.0
    extracted: dict = {}

    if quality_status != "illisible" and raw_text.strip():
        if doc_type and doc_type not in ("PENDING", "AUTRE"):
            detected_type = doc_type
            cls_confidence = 1.0
        else:
            try:
                detected_type, cls_confidence, _ = classify_document(raw_text)
            except Exception as e:
                logger.warning(f"[Classify] échec : {e}")

        # Extraction
        if detected_type and detected_type not in ("AUTRE", "PENDING"):
            try:
                extracted = extract_data(detected_type, raw_text)
            except Exception as e:
                logger.warning(f"[Extract] échec : {e}")
                extracted = {}

    doc_status = "REJECTED" if quality_status == "illisible" else "EXTRACTED"

    # Mise à jour du document
    document.type = detected_type if detected_type != "PENDING" else (doc_type or "AUTRE")
    document.status = doc_status
    document.ocr_provider = ocr_provider_used
    document.ocr_confidence = ocr_confidence
    document.ocr_raw_text = raw_text
    document.extracted_data = extracted
    document.classification_confidence = cls_confidence
    document.auto_classified = doc_type is None

    # Auto-détection VN/VO et extraction des champs du dossier
    if detected_type in ("COC", "FACTURE", "CG_BARREE"):
        # Construire le dict dossier pour le pipeline
        dossier_dict = await _build_dossier_dict(db, dossier)
        try:
            new_type = _auto_detect_dossier_type(dossier_dict)
            if new_type and not dossier.type:
                dossier.type = new_type
        except Exception as e:
            logger.warning(f"[AutoDetect] échec : {e}")

        try:
            updates = _auto_extract_dossier_fields(dossier_dict)
            for k, v in (updates or {}).items():
                if hasattr(dossier, k) and not getattr(dossier, k):
                    setattr(dossier, k, v)
        except Exception as e:
            logger.warning(f"[AutoExtract dossier] échec : {e}")

    if detected_type in ("CNI", "PASSEPORT", "PERMIS", "DOMICILE"):
        dossier_dict = await _build_dossier_dict(db, dossier)
        try:
            updates = _auto_extract_client_fields(dossier_dict)
            for k, v in (updates or {}).items():
                if hasattr(dossier, k) and not getattr(dossier, k):
                    setattr(dossier, k, v)
        except Exception as e:
            logger.warning(f"[AutoExtract client] échec : {e}")

    await db.flush()

    return {
        "document_id": document.id,
        "dossier_id": dossier_id,
        "type": document.type,
        "status": document.status,
        "ocr": {
            "provider": ocr_provider_used,
            "confidence": ocr_confidence,
            "quality": quality_status,
            "message": quality_message,
        },
        "classification": {
            "detected": detected_type,
            "confidence": cls_confidence,
        },
        "extracted": extracted,
    }


@router.get("/{document_id}")
async def get_document(document_id: str, db: AsyncSession = Depends(get_db)):
    """Récupère le détail d'un document (métadonnées + extraction)."""
    doc = await db.get(DocumentDB, document_id)
    if not doc:
        raise HTTPException(404, "Document non trouvé")
    return {
        "id": doc.id,
        "dossier_id": doc.dossier_id,
        "type": doc.type,
        "status": doc.status,
        "filename": doc.original_filename,
        "mime_type": doc.mime_type,
        "file_size_bytes": doc.file_size_bytes,
        "ocr": {
            "provider": doc.ocr_provider,
            "confidence": doc.ocr_confidence,
        },
        "extracted_data": doc.extracted_data,
        "validation_result": doc.validation_result,
        "source_email_subject": doc.source_email_subject,
        "source_email_from": doc.source_email_from,
        "created_at": doc.created_at.isoformat() if doc.created_at else None,
    }


# ─── Helpers internes ───────────────────────────────────────────────────────


async def _sync_profil_pro(db: AsyncSession, professionnel_id: str) -> None:
    """
    Peuple la variable PROFIL_PRO du moteur realtime depuis la BDD locale.
    Le moteur travaille avec des dicts — c'est le pont avec SQLAlchemy.
    """
    from api.models.professionnel import Professionnel
    pro = await db.get(Professionnel, professionnel_id)
    if pro:
        set_profil_pro({
            "nom_commerce": pro.nom_commerce,
            "adresse": pro.adresse,
            "telephone_commerce": pro.telephone_commerce,
            "email_commerce": pro.email_commerce,
            "cachet_path": pro.cachet_path,
            "signature_path": pro.signature_path,
            "kbis_path": pro.kbis_path,
            "siret": pro.siret,
            "raison_sociale": pro.raison_sociale,
        })


async def _build_dossier_dict(db: AsyncSession, dossier: DossierDB) -> dict:
    """
    Construit un dict compatible avec le moteur realtime depuis le dossier BDD.

    Le moteur de vérification travaille sur des dicts plats — cette fonction
    fait le pont entre SQLAlchemy et le pipeline.
    """
    await _sync_profil_pro(db, dossier.professionnel_id)

    result = await db.execute(
        select(DocumentDB).where(DocumentDB.dossier_id == dossier.id)
    )
    docs = result.scalars().all()

    docs_list = []
    for doc in docs:
        d = {
            "id": doc.id,
            "type": doc.type or "PENDING",
            "filename": doc.original_filename,
            "storage_path": doc.storage_path,
            "status": doc.status,
            "extracted_data": doc.extracted_data or {},
            "ocr_confidence": doc.ocr_confidence,
            "quality": {
                "status": (
                    "ok" if doc.status == "EXTRACTED"
                    else "illisible" if doc.status == "REJECTED"
                    else "en_cours"
                ),
                "confidence": doc.ocr_confidence,
            },
        }
        docs_list.append(d)

    # En version locale, il n'y a plus de distinction vendeur/client.
    # Tous les documents arrivent par l'agent. On garde la structure attendue
    # par le pipeline existant en mettant tout dans documents_vendeur pour
    # rester compatible (le pipeline sera nettoyé en Phase 3.7).
    return {
        "id": dossier.id,
        "type": dossier.type,
        "client_telephone": dossier.client_telephone,
        "client_email": dossier.client_email,
        "client_nom": dossier.client_nom,
        "client_prenom": dossier.client_prenom,
        "vin": dossier.vin,
        "immatriculation": dossier.immatriculation,
        "is_personne_morale": dossier.is_personne_morale,
        "documents_vendeur": docs_list,
        "documents_client": [],
        "documents": docs_list,
        "status": dossier.status,
    }
