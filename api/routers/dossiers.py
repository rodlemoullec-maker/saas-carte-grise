"""
Router dossiers — CRUD + upload documents.

POST   /dossiers/              Créer un nouveau dossier
GET    /dossiers/              Lister les dossiers (filtres, pagination)
GET    /dossiers/{id}          Détail d'un dossier
POST   /dossiers/{id}/submit   Soumettre au SIV (si ACCEPTE)
DELETE /dossiers/{id}          Annuler un dossier
"""
from __future__ import annotations
from fastapi import APIRouter
router = APIRouter()

@router.post("/")
async def create_dossier():
    # TODO: valider le type de dossier + créer en BDD + déclencher pipeline Celery
    raise NotImplementedError

@router.get("/")
async def list_dossiers():
    # TODO: filtres status/type/date + pagination
    raise NotImplementedError

@router.get("/{dossier_id}")
async def get_dossier(dossier_id: str):
    # TODO: retourner dossier complet avec documents + résultats cross-checks
    raise NotImplementedError

@router.post("/{dossier_id}/submit")
async def submit_dossier(dossier_id: str):
    # TODO: vérifier statut ACCEPTE + déclencher soumission SIV
    raise NotImplementedError

@router.delete("/{dossier_id}")
async def cancel_dossier(dossier_id: str):
    raise NotImplementedError
