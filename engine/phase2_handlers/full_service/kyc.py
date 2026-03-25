"""
Phase 2 — Full Service : KYC anti-fraude (NIV.2 systématique + NIV.3 conditionnel)

Flux :
  AUTHENTIQUE → soumission SIV directe (NIV.3 sauté)
  SUSPECT     → file d'attente contrôle opérateur (NIV.3, ~10% des dossiers)
  REJETÉ      → blocage automatique + notification pro

Fournisseurs KYC envisagés : Ariadnext, IDnow
"""
from __future__ import annotations

from enum import Enum
from dataclasses import dataclass
from typing import Optional


class KYCResult(str, Enum):
    AUTHENTIQUE = "AUTHENTIQUE"
    SUSPECT = "SUSPECT"
    REJETE = "REJETE"


@dataclass
class KYCResponse:
    result: KYCResult
    confidence: float          # 0.0 → 1.0
    provider: str              # "ariadnext" | "idnow"
    reference_id: str
    details: Optional[dict] = None


class KYCService:
    """
    NIV.2 — Authentification automatique des documents d'identité.

    TODO:
    - Implémenter l'intégration Ariadnext (API REST)
    - Implémenter l'intégration IDnow en fallback
    - Définir les seuils confidence : AUTHENTIQUE >= 0.85, SUSPECT 0.60-0.85, REJETÉ < 0.60
    - Logger chaque résultat KYC dans la table kyc_results (audit RGPD)
    """

    async def verify(self, document_path: str, document_type: str) -> KYCResponse:
        """
        Soumet un document au service KYC et retourne le résultat.

        Args:
            document_path: Chemin du fichier image/PDF du document
            document_type: "CNI" | "PASSEPORT" | "TITRE_SEJOUR"

        Returns:
            KYCResponse avec le verdict NIV.2

        Raises:
            KYCProviderError: Si le fournisseur KYC est indisponible
        """
        raise NotImplementedError("TODO: implémenter intégration KYC (Ariadnext/IDnow)")

    def requires_niv3_review(self, response: KYCResponse) -> bool:
        """Retourne True si le dossier doit passer en contrôle visuel opérateur (NIV.3)."""
        return response.result == KYCResult.SUSPECT
