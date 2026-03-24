"""
Client API SIV / ANTS — Système d'Immatriculation des Véhicules.

Deux usages :
1. Vérification préalable : ce VIN est-il déjà immatriculé ?
2. Soumission du dossier pour obtention de la carte grise.

IMPORTANT :
- L'accès SIV nécessite une habilitation officielle délivrée par l'ANTS
- L'environnement sandbox est disponible pour les tests
- Chaque requête doit être loggée (audit trail réglementaire)
- Les données transmises sont soumises au secret professionnel

TODO: intégrer les specs techniques de l'API ANTS une fois l'habilitation obtenue.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum


class SIVEnvironment(str, Enum):
    SANDBOX = "sandbox"
    PRODUCTION = "production"


@dataclass
class SIVVehicleStatus:
    vin: str
    is_registered: bool
    immatriculation: str | None     # Numéro de plaque si immatriculé
    titulaire: str | None           # Nom du titulaire si immatriculé
    date_premiere_immat: datetime | None


@dataclass
class SIVSubmissionResult:
    success: bool
    reference: str | None           # Numéro de suivi SIV
    status: str | None
    estimated_delivery: datetime | None
    errors: list[str]


class SIVAntsClient:
    """
    Client pour l'API SIV de l'ANTS.

    TODO: remplir les endpoints exacts après obtention de la documentation ANTS.
    TODO: implémenter l'authentification (certificat client + clé API).
    TODO: implémenter le format exact du payload SIV pour chaque type de dossier.
    TODO: implémenter le suivi du statut post-soumission (polling ou webhook).
    """

    def __init__(
        self,
        api_key: str,
        habilitation_id: str,
        environment: SIVEnvironment = SIVEnvironment.SANDBOX,
    ) -> None:
        self.api_key = api_key
        self.habilitation_id = habilitation_id
        self.environment = environment

    async def check_vin_registration(self, vin: str) -> SIVVehicleStatus:
        """
        Vérifie si un VIN est déjà immatriculé dans le SIV.
        Utilisé avant soumission pour valider qu'un véhicule neuf est bien "vierge".

        TODO: implémenter l'appel SIV.
        TODO: logger chaque appel (audit trail obligatoire).
        """
        raise NotImplementedError

    async def submit_dossier(self, payload: dict) -> SIVSubmissionResult:
        """
        Soumet un dossier complet au SIV ANTS.

        Le payload est spécifique au type de dossier
        (NEUF_PRO_PARTICULIER, OCCASION, etc.).

        TODO: valider le payload contre le schéma SIV avant envoi.
        TODO: implémenter la soumission.
        TODO: implémenter la gestion des erreurs SIV (codes retour).
        TODO: logger le payload et la réponse (sans données sensibles en clair).
        """
        raise NotImplementedError

    async def get_dossier_status(self, reference: str) -> dict:
        """
        Suit le statut d'un dossier après soumission.

        TODO: implémenter le polling de statut.
        """
        raise NotImplementedError

    def build_payload_neuf(self, dossier_data: dict) -> dict:
        """
        Construit le payload SIV pour un dossier NEUF_PRO_PARTICULIER.

        TODO: implémenter selon les specs techniques ANTS.
        """
        raise NotImplementedError
