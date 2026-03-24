"""
Router documents — upload et gestion des fichiers.

POST   /documents/{dossier_id}/upload     Uploader un document
GET    /documents/{document_id}           Détail + résultat extraction
PUT    /documents/{document_id}/reupload  Remplacer un document
"""
from __future__ import annotations
from fastapi import APIRouter, UploadFile
router = APIRouter()

@router.post("/{dossier_id}/upload")
async def upload_document(dossier_id: str, file: UploadFile, doc_type: str):
    # TODO: valider MIME (PDF/JPG/PNG), taille max 10MB
    # TODO: stocker + SHA-256 + créer Document en BDD + déclencher OCR Celery
    raise NotImplementedError

@router.get("/{document_id}")
async def get_document(document_id: str):
    # TODO: retourner Document + extracted_data + validation_result
    raise NotImplementedError

@router.put("/{document_id}/reupload")
async def reupload_document(document_id: str, file: UploadFile):
    # TODO: remplacer le fichier + relancer OCR
    raise NotImplementedError
