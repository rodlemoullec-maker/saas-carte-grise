"""
Router webhooks — callbacks entrants SIV ANTS.
"""
from __future__ import annotations
from fastapi import APIRouter, Request
router = APIRouter()

@router.post("/siv/status")
async def siv_status_callback(request: Request):
    # TODO: vérifier signature webhook + parser payload + MAJ statut + notifier
    raise NotImplementedError
