"""
Worker notifications — envoi emails et SMS.

Tâches Celery :
  send_status_update(dossier_id, new_status)   → notifier pro + client
  send_correction_request(dossier_id, issues)  → notifier corrections requises
  send_siv_confirmation(dossier_id)            → CG en cours d'envoi

TODO: implémenter les tâches Celery.
"""
from __future__ import annotations

def send_status_update(dossier_id: str, new_status: str) -> None:
    raise NotImplementedError

def send_correction_request(dossier_id: str, issues: list) -> None:
    raise NotImplementedError
