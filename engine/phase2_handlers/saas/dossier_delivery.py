"""
Phase 2 — SaaS : Livraison du dossier prêt à soumettre.

Le pro habilité SIV reçoit dans son portail un récapitulatif complet
contenant toutes les données vérifiées + KYC + estimation taxes + checklist.
Il soumet lui-même dans son accès SIV. On ne touche pas aux taxes.

Contenu du livrable :
  - Récapitulatif structuré (données à saisir dans le SIV)
  - Résultat KYC (AUTHENTIQUE / SUSPECT + note si suspect)
  - Estimation taxes indicative (taxe régionale + malus + gestion + acheminement)
  - Checklist validation finale (NIV.3 pro, assurance active, etc.)
  - Résultat Phase 0 HistoVec si VO
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional
from decimal import Decimal


@dataclass
class TaxEstimate:
    """
    Estimation indicative des taxes. Montant exact confirmé par le SIV lors de la saisie.
    """
    taxe_regionale: Decimal     # CV fiscaux × tarif régional (dépt du domicile)
    malus_co2: Decimal          # Calculé sur CO2 WLTP (barème en vigueur)
    frais_gestion: Decimal      # 11€ fixe ANTS
    acheminement: Decimal       # 2.76€ fixe
    total_estime: Decimal

    departement: str
    cv_fiscaux: int
    co2_wltp: Optional[int]

    disclaimer: str = (
        "Estimation indicative calculée avant saisie SIV. "
        "Le montant exact sera affiché par le SIV au moment de la saisie."
    )


@dataclass
class ChecklistItem:
    label: str
    mandatory: bool = True
    checked: bool = False


@dataclass
class DossierPret:
    """
    Livrable complet remis au pro SaaS après Phase 2.

    TODO: Générer un PDF ou une page HTML structurée dans le portail.
    """
    dossier_id: str

    # Identité
    nom_naissance: str
    prenoms: str
    date_naissance: str
    lieu_naissance: str
    adresse_complete: str

    # Véhicule
    vin: str
    cnit: str
    marque: str
    modele: str
    energie: str
    puissance_kw: float
    co2_wltp: Optional[int]
    puissance_fiscale: int
    places_assises: int

    # VN only
    immatriculation_existante: Optional[str] = None

    # KYC
    kyc_result: str = ""           # "AUTHENTIQUE" | "SUSPECT"
    kyc_note: Optional[str] = None # Note si SUSPECT

    # Taxes
    estimation_taxes: Optional[TaxEstimate] = None

    # HistoVec (VO uniquement)
    histovec_result: Optional[dict] = None

    # Checklist finale
    checklist: list[ChecklistItem] = field(default_factory=lambda: [
        ChecklistItem("VIN vérifié sur le véhicule physique"),
        ChecklistItem("Identité contrôlée en présentiel (NIV.1 effectué)"),
        ChecklistItem("Assurance active au jour de la saisie"),
        ChecklistItem("Cerfa 13749 signé client en votre possession"),
        ChecklistItem("Mandat 13757 signé client en votre possession"),
    ])


class DossierDeliveryService:
    """
    Prépare et envoie le dossier prêt au portail du pro.

    TODO:
    - Implémenter le calcul de TaxEstimate (barèmes régionaux + malus CO2 en vigueur)
    - Générer le PDF récapitulatif signé numériquement
    - Notifier le pro (email + push portail)
    - Déclencher le débit des honoraires (pré-auth CB)
    - Adapter la checklist selon type dossier (VN/VO, PM, co-tit, hébergé...)
    """

    async def build(self, dossier_id: str, kyc_result: str) -> DossierPret:
        """Construit le DossierPret à partir des données du dossier traité."""
        raise NotImplementedError

    async def deliver(self, dossier: DossierPret) -> None:
        """Dépose le dossier dans le portail du pro et déclenche la notification."""
        raise NotImplementedError
