"""
Router décisions — résultats et overrides agent.

GET    /decisions/{dossier_id}           Résultat décision
POST   /decisions/{dossier_id}/override  Agent override (REVUE_AGENT → ACCEPTE/REJET)
POST   /decisions/{dossier_id}/retry     Relancer le pipeline
"""
from __future__ import annotations
from fastapi import APIRouter
router = APIRouter()

@router.get("/{dossier_id}")
async def get_decision(dossier_id: str):
    raise NotImplementedError

@router.post("/{dossier_id}/override")
async def agent_override(dossier_id: str):
    # TODO: vérifier rôle AGENT_HABILITE + logger décision (audit trail) + MAJ statut
    raise NotImplementedError

@router.post("/{dossier_id}/retry")
async def retry_pipeline(dossier_id: str):
    # TODO: vérifier statut CORRECTION + relancer pipeline complet
    raise NotImplementedError
