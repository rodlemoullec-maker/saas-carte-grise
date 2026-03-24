"""
Classe de base pour les croisements inter-documents.
"""
from __future__ import annotations

from abc import ABC, abstractmethod

from engine.models.decision import CrossCheckResult


class BaseCrossCheck(ABC):
    """
    Un CrossCheck compare des données extraites de documents différents
    et retourne un ou plusieurs CrossCheckResult.
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Identifiant unique du croisement (ex: 'vin_coc_facture')."""
        ...

    @abstractmethod
    def run(self, *args, **kwargs) -> list[CrossCheckResult]:
        """Exécute le croisement et retourne les résultats."""
        ...
