"""
Phase 2 — SaaS : KYC anti-fraude (même logique NIV.2 que Full Service).

Différence vs Full Service :
  - AUTHENTIQUE → livraison dossier prêt directement
  - SUSPECT → alerte au pro "vérifier original en portail" (pas de NIV.3 opérateur)
  - REJETÉ → blocage + notification pro

Le NIV.3 est délégué au pro (il a déjà vu le client en NIV.1).
"""
from engine.phase2_handlers.full_service.kyc import KYCService, KYCResponse, KYCResult

# Réutilise exactement le même service KYC — seule la logique post-résultat diffère
__all__ = ["KYCService", "KYCResponse", "KYCResult"]
