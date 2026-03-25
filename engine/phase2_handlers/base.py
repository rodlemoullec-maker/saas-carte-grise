"""
Interface commune pour les deux handlers Phase 2.

Full Service  → FullServicePhase2Handler
SaaS          → SaaSPhase2Handler

Les deux implémentent la même interface Phase2Handler.
Le choix du handler est déterminé par ServiceMode sur le tenant (professionnel).
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from enum import Enum


class ServiceMode(str, Enum):
    FULL_SERVICE = "FULL_SERVICE"   # Pro non habilité SIV
    SAAS = "SAAS"                   # Pro déjà habilité SIV


class Phase2Handler(ABC):
    """Interface commune Phase 2."""

    @abstractmethod
    async def run_kyc(self, dossier_id: str) -> dict:
        """Lance le KYC NIV.2 et retourne le résultat."""
        ...

    @abstractmethod
    async def finalize(self, dossier_id: str, kyc_result: dict) -> None:
        """
        Full Service : soumet au SIV via extension.
        SaaS        : prépare et livre le dossier prêt au pro.
        """
        ...


def get_phase2_handler(mode: ServiceMode) -> Phase2Handler:
    """Factory — retourne le bon handler selon le mode de service du tenant."""
    if mode == ServiceMode.FULL_SERVICE:
        from engine.phase2_handlers.full_service.handler import FullServicePhase2Handler
        return FullServicePhase2Handler()
    elif mode == ServiceMode.SAAS:
        from engine.phase2_handlers.saas.handler import SaaSPhase2Handler
        return SaaSPhase2Handler()
    raise ValueError(f"ServiceMode inconnu : {mode}")
