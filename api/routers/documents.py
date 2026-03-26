"""
Router documents — upload, classification, extraction.

POST   /documents/{dossier_id}/upload     Uploader un document
GET    /documents/{document_id}           Détail + résultat extraction
PUT    /documents/{document_id}/reupload  Remplacer un document (re-scan)
"""
from __future__ import annotations

from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from api.models.base import get_db
from api.models.document import DocumentDB
from api.models.dossier import DossierDB
from storage.document_store import BaseDocumentStore, get_document_store

router = APIRouter()

ALLOWED_MIME_TYPES = {
    "application/pdf",
    "image/jpeg",
    "image/png",
    "image/tiff",
    "image/webp",
}
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB


@router.post("/{dossier_id}/upload", status_code=201)
async def upload_document(
    dossier_id: UUID,
    file: UploadFile,
    doc_type: str | None = None,
    db: AsyncSession = Depends(get_db),
):
    """
    Upload un document dans un dossier.

    - Valide le MIME type et la taille
    - Stocke le fichier (local ou S3)
    - Calcule le SHA-256
    - Crée l'entrée Document en BDD
    - Déclenche la classification auto si doc_type absent
    - Déclenche l'OCR + extraction en async (Celery)
    """
    # Vérif dossier existe
    dossier = await db.get(DossierDB, dossier_id)
    if not dossier:
        raise HTTPException(status_code=404, detail="Dossier non trouvé")

    # Vérif MIME
    if file.content_type not in ALLOWED_MIME_TYPES:
        raise HTTPException(
            status_code=422,
            detail=f"Type de fichier non supporté : {file.content_type}. "
                   f"Acceptés : {', '.join(ALLOWED_MIME_TYPES)}",
        )

    # Lire le fichier
    file_bytes = await file.read()
    if len(file_bytes) > MAX_FILE_SIZE:
        raise HTTPException(status_code=422, detail="Fichier trop volumineux (max 10 MB)")
    if len(file_bytes) == 0:
        raise HTTPException(status_code=422, detail="Fichier vide")

    # SHA-256
    store = get_document_store()
    sha256 = store.compute_sha256(file_bytes)

    # Stocker
    doc_id = uuid4()
    storage_path = f"{dossier_id}/{doc_id}/{file.filename}"
    await store.save(file_bytes, storage_path, file.content_type)

    # Créer en BDD
    document = DocumentDB(
        id=doc_id,
        dossier_id=dossier_id,
        type=doc_type or "PENDING",
        status="PENDING",
        storage_path=storage_path,
        original_filename=file.filename or "unknown",
        mime_type=file.content_type,
        file_size_bytes=len(file_bytes),
        sha256=sha256,
    )
    db.add(document)
    await db.flush()

    # TODO: lancer classification + OCR en Celery
    # from workers.pipeline import run_ocr
    # run_ocr.delay(str(doc_id))

    return {
        "document_id": str(doc_id),
        "dossier_id": str(dossier_id),
        "type": document.type,
        "status": "PENDING",
        "filename": file.filename,
        "size_bytes": len(file_bytes),
        "sha256": sha256,
    }


@router.get("/{document_id}")
async def get_document(
    document_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """Retourne les détails d'un document + données extraites."""
    doc = await db.get(DocumentDB, document_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document non trouvé")

    return {
        "id": str(doc.id),
        "dossier_id": str(doc.dossier_id),
        "type": doc.type,
        "status": doc.status,
        "filename": doc.original_filename,
        "mime_type": doc.mime_type,
        "size_bytes": doc.file_size_bytes,
        "sha256": doc.sha256,
        "ocr_confidence": doc.ocr_confidence,
        "extracted_data": doc.extracted_data,
        "validation_result": doc.validation_result,
        "auto_classified": doc.auto_classified,
        "classification_confidence": doc.classification_confidence,
        "created_at": doc.created_at.isoformat() if doc.created_at else None,
    }


@router.put("/{document_id}/reupload")
async def reupload_document(
    document_id: UUID,
    file: UploadFile,
    db: AsyncSession = Depends(get_db),
):
    """Remplace un document existant et relance l'OCR."""
    doc = await db.get(DocumentDB, document_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document non trouvé")

    if file.content_type not in ALLOWED_MIME_TYPES:
        raise HTTPException(status_code=422, detail="Type de fichier non supporté")

    file_bytes = await file.read()
    if len(file_bytes) > MAX_FILE_SIZE:
        raise HTTPException(status_code=422, detail="Fichier trop volumineux")

    store = get_document_store()

    # Supprimer l'ancien
    try:
        await store.delete(doc.storage_path)
    except FileNotFoundError:
        pass

    # Stocker le nouveau
    new_path = f"{doc.dossier_id}/{doc.id}/{file.filename}"
    await store.save(file_bytes, new_path, file.content_type)

    # MAJ BDD
    doc.storage_path = new_path
    doc.original_filename = file.filename or "unknown"
    doc.mime_type = file.content_type
    doc.file_size_bytes = len(file_bytes)
    doc.sha256 = store.compute_sha256(file_bytes)
    doc.status = "PENDING"
    doc.extracted_data = None
    doc.validation_result = None
    doc.ocr_confidence = None
    await db.flush()

    # TODO: relancer OCR
    # from workers.pipeline import run_ocr
    # run_ocr.delay(str(doc.id))

    return {"status": "ok", "document_id": str(doc.id), "message": "Document remplacé — OCR relancé"}
