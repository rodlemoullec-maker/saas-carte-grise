"""
Worker pipeline — orchestration du traitement d'un dossier.

Tâches Celery :
  process_dossier(dossier_id)   → pipeline complet
  run_ocr(document_id)          → OCR + extraction d'un document
  run_cross_checks(dossier_id)  → croisements inter-documents
  submit_to_siv(dossier_id)     → soumission SIV ANTS

TODO: configurer Celery app avec Redis broker.
TODO: implémenter chaque tâche.
TODO: gérer les retries (max 3, backoff exponentiel).
TODO: mettre à jour le statut dossier/document à chaque étape.
"""
from __future__ import annotations
# TODO: from celery import Celery
# TODO: from config.settings import get_settings

# app = Celery("pipeline", broker=get_settings().celery_broker_url)

def process_dossier(dossier_id: str) -> None:
    """
    Pipeline complet pour un dossier :
    1. Vérifier que tous les documents obligatoires sont présents
    2. Pour chaque document : OCR + extraction + validation individuelle
    3. Croisements inter-documents
    4. Calcul du score + décision
    5. MAJ statut dossier + notification

    TODO: implémenter.
    """
    raise NotImplementedError

def run_ocr(document_id: str) -> None:
    """Lance l'OCR + extraction structurée sur un document."""
    raise NotImplementedError

def run_cross_checks(dossier_id: str) -> None:
    """Lance tous les croisements inter-documents."""
    raise NotImplementedError

def submit_to_siv(dossier_id: str) -> None:
    """Prépare le payload et soumet au SIV ANTS."""
    raise NotImplementedError
