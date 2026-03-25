"""
Handler Phase 2 — SaaS
Pro déjà habilité SIV — On prépare, le pro soumet.

Flux :
  run_kyc()   → NIV.2 (même service que Full Service)
  finalize()  → si AUTHENTIQUE : DossierDeliveryService.deliver()
              → si SUSPECT     : alerte pro + livraison avec note
              → si REJETÉ      : blocage + notification pro
"""
from __future__ import annotations

from engine.phase2_handlers.base import Phase2Handler
from engine.phase2_handlers.full_service.kyc import KYCService, KYCResult
from engine.phase2_handlers.saas.dossier_delivery import DossierDeliveryService


class SaaSPhase2Handler(Phase2Handler):

    def __init__(self):
        self.kyc_service = KYCService()
        self.delivery_service = DossierDeliveryService()

    async def run_kyc(self, dossier_id: str) -> dict:
        """
        TODO: Identique Full Service — même service KYC NIV.2.
        """
        raise NotImplementedError

    async def finalize(self, dossier_id: str, kyc_result: dict) -> None:
        """
        TODO:
        - AUTHENTIQUE → DossierDeliveryService.build() + .deliver()
        - SUSPECT     → Construire dossier avec note d'alerte + .deliver()
                        (le pro fait lui-même le NIV.3 — il a vu le client)
        - REJETÉ      → Mettre dossier en REJET + notifier pro
        """
        raise NotImplementedError
