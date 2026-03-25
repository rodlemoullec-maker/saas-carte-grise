"""
Phase 2 — Full Service : Soumission SIV via extension navigateur semi-automatique.

Flux :
  1. L'extension pré-remplit le formulaire web SIV depuis les données du dossier
  2. L'opérateur vérifie les champs (~30 secondes) et valide d'un clic
  3. SIV affiche le montant exact des taxes
  4. L'opérateur déclenche le paiement CB du pro (enregistrée dans le portail)
  5. Le SIV génère le CPI
  6. L'extension récupère le CPI automatiquement
  7. En mode BATCH : enchaîne le dossier suivant automatiquement

Particularités VN : pas d'interrogation SIV préalable (véhicule jamais immatriculé)
Particularités VO : interrogation SIV préalable obligatoire (étape 13)
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional
from enum import Enum


class SubmissionMode(str, Enum):
    VN = "VN"   # 1ère immatriculation
    VO = "VO"   # Changement de titulaire


@dataclass
class SIVPayload:
    """
    Données structurées envoyées à l'extension navigateur pour pré-remplissage.

    TODO: Mapper exactement aux champs du formulaire SIV ANTS.
    Référence : formulaire web SIV (cartegrise.ants.gouv.fr)
    """
    mode: SubmissionMode

    # Identité titulaire
    nom_naissance: str
    prenoms: str
    date_naissance: str    # JJ/MM/AAAA
    lieu_naissance: str
    adresse: str
    code_postal: str
    commune: str

    # Véhicule
    vin: str
    cnit: str
    marque: str
    energie: str
    puissance_kw: float
    co2_wltp: Optional[int]
    places_assises: int

    # Spécifique VO
    immatriculation: Optional[str] = None
    ancien_titulaire: Optional[str] = None

    # Métadonnées dossier
    dossier_id: str = ""
    pro_id: str = ""
    cb_token: str = ""     # Token CB pro enregistrée (Stripe/PayPlug)


@dataclass
class SIVResult:
    success: bool
    cpi_url: Optional[str]
    immatriculation_attribuee: Optional[str]
    montant_taxes_exact: Optional[float]
    error_message: Optional[str] = None
    siv_reference: Optional[str] = None


class SIVSubmissionService:
    """
    Gère la communication avec l'extension navigateur pour la soumission SIV.

    TODO:
    - Définir le protocole de communication extension ↔ backend
      (WebSocket ou polling API)
    - Implémenter la file d'attente BATCH (Celery task)
    - Gérer les rejets SIV : parser le message d'erreur, notifier pro, relancer
    - Implémenter la récupération automatique du CPI depuis l'extension
    - Gérer la CB pro : intégration Stripe/PayPlug pour le débit taxes
    """

    async def prepare_payload(self, dossier_id: str) -> SIVPayload:
        """Construit le payload SIV à partir des données extraites du dossier."""
        raise NotImplementedError

    async def submit(self, payload: SIVPayload) -> SIVResult:
        """Envoie le payload à l'extension et attend le résultat."""
        raise NotImplementedError

    async def submit_batch(self, dossier_ids: list[str]) -> list[SIVResult]:
        """Mode batch : enchaîne plusieurs dossiers automatiquement."""
        raise NotImplementedError
