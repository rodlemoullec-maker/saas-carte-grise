"""
Handler Phase 2 — Full Service
Pro non habilité SIV — On gère tout.

Flux :
  run_kyc()   → NIV.2 (Ariadnext/IDnow)
  finalize()  → si AUTHENTIQUE : soumission SIV via extension
              → si SUSPECT     : queue contrôle opérateur NIV.3
              → si REJETÉ      : blocage + notification pro
"""
from __future__ import annotations

from engine.phase2_handlers.base import Phase2Handler
from engine.phase2_handlers.full_service.kyc import KYCService, KYCResult
from engine.phase2_handlers.full_service.siv_submission import SIVSubmissionService


class FullServicePhase2Handler(Phase2Handler):

    def __init__(self):
        self.kyc_service = KYCService()
        self.siv_service = SIVSubmissionService()

    async def run_kyc(self, dossier_id: str) -> dict:
        """
        TODO:
        1. Récupérer le chemin CNI du dossier
        2. Appeler KYCService.verify()
        3. Stocker le résultat en base (table kyc_results)
        4. Retourner le résultat structuré
        """
        raise NotImplementedError

    async def finalize(self, dossier_id: str, kyc_result: dict) -> None:
        """
        TODO:
        - AUTHENTIQUE → SIVSubmissionService.submit()
        - SUSPECT     → Créer une tâche dans la review queue opérateur
        - REJETÉ      → Mettre dossier en REJET + notifier pro
        """
        raise NotImplementedError
