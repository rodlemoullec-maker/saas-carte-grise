"""
Paiement des HONORAIRES — c'est l'argent du porteur de projet.

Pre-autorisation CB au moment du GO/NO-GO.
Debit uniquement sur dossiers aboutis (CPI genere).
Alternative : facture mensuelle + prelevement SEPA pour pros a volume.

Provider : Stripe ou PayPlug (configurable).

SEPARATION CLAIRE :
  - Ce module gere UNIQUEMENT les honoraires (30-60 EUR Full Service, 10-25 EUR SaaS)
  - Les taxes d'immatriculation sont gerees par taxes_siv.py (mecanisme different)
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from enum import Enum
from uuid import UUID

logger = logging.getLogger(__name__)


class PaymentProvider(str, Enum):
    STRIPE = "stripe"
    PAYPLUG = "payplug"


class PaymentMode(str, Enum):
    UNITAIRE = "UNITAIRE"      # Pre-auth CB par dossier
    ABONNEMENT = "ABONNEMENT"  # Facture mensuelle + SEPA


@dataclass
class PreauthResult:
    success: bool
    preauth_id: str | None = None
    error: str | None = None
    amount_cents: int = 0


@dataclass
class CaptureResult:
    success: bool
    payment_id: str | None = None
    error: str | None = None
    amount_cents: int = 0


class HonorairesService:
    """
    Gere le paiement des honoraires (argent du porteur de projet).

    Flux unitaire :
      1. GO/NO-GO → preauthorize(montant, carte_pro)
      2. CPI genere → capture(preauth_id)
      3. Dossier annule → cancel_preauth(preauth_id)

    Flux abonnement :
      1. Fin de mois → invoice(pro_id, dossiers_aboutis)
      2. SEPA prelevement automatique
    """

    def __init__(self, provider: PaymentProvider = PaymentProvider.STRIPE):
        self.provider = provider

    async def preauthorize(
        self,
        dossier_id: UUID,
        professionnel_id: UUID,
        amount_cents: int,
        stripe_customer_id: str | None = None,
    ) -> PreauthResult:
        """
        Pre-autorisation CB au moment du GO/NO-GO.
        Le montant n'est PAS debite — reserve seulement.
        Valide 7 jours (Stripe) ou 7 jours (PayPlug).
        """
        logger.info(
            f"[Honoraires] Pre-auth {amount_cents/100:.2f} EUR "
            f"dossier={dossier_id} pro={professionnel_id}"
        )

        if self.provider == PaymentProvider.STRIPE:
            return await self._stripe_preauth(amount_cents, stripe_customer_id, dossier_id)
        else:
            return await self._payplug_preauth(amount_cents, dossier_id)

    async def capture(self, preauth_id: str, amount_cents: int | None = None) -> CaptureResult:
        """
        Debite le montant pre-autorise. Appele uniquement quand le CPI est genere.
        amount_cents optionnel pour debit partiel (si le montant final differe).
        """
        logger.info(f"[Honoraires] Capture preauth={preauth_id}")

        # TODO: appel Stripe/PayPlug
        # stripe.PaymentIntent.capture(preauth_id, amount_to_capture=amount_cents)
        return CaptureResult(success=True, payment_id=preauth_id, amount_cents=amount_cents or 0)

    async def cancel_preauth(self, preauth_id: str) -> bool:
        """Annule la pre-autorisation (dossier annule ou rejete)."""
        logger.info(f"[Honoraires] Annulation preauth={preauth_id}")
        # TODO: stripe.PaymentIntent.cancel(preauth_id)
        return True

    async def create_monthly_invoice(
        self,
        professionnel_id: UUID,
        dossiers_aboutis: list[dict],
        tarif_unitaire_cents: int,
    ) -> dict:
        """
        Genere une facture mensuelle pour les pros en mode abonnement.
        Prelevement SEPA automatique.
        """
        total = len(dossiers_aboutis) * tarif_unitaire_cents
        logger.info(
            f"[Honoraires] Facture mensuelle pro={professionnel_id} "
            f"{len(dossiers_aboutis)} dossiers x {tarif_unitaire_cents/100:.2f} EUR = {total/100:.2f} EUR"
        )
        # TODO: Stripe Invoice API ou generation PDF + SEPA
        return {
            "professionnel_id": str(professionnel_id),
            "nb_dossiers": len(dossiers_aboutis),
            "total_cents": total,
            "status": "pending",
        }

    # ─── Providers ────────────────────────────────────────────────────────

    async def _stripe_preauth(self, amount_cents, customer_id, dossier_id) -> PreauthResult:
        """Pre-auth via Stripe PaymentIntent."""
        # TODO: implementer avec stripe SDK
        # import stripe
        # intent = stripe.PaymentIntent.create(
        #     amount=amount_cents,
        #     currency="eur",
        #     customer=customer_id,
        #     capture_method="manual",  # Pre-auth, pas de debit immediat
        #     metadata={"dossier_id": str(dossier_id)},
        # )
        # return PreauthResult(success=True, preauth_id=intent.id, amount_cents=amount_cents)
        return PreauthResult(success=True, preauth_id=f"pi_mock_{dossier_id}", amount_cents=amount_cents)

    async def _payplug_preauth(self, amount_cents, dossier_id) -> PreauthResult:
        """Pre-auth via PayPlug."""
        # TODO: implementer avec PayPlug API
        return PreauthResult(success=True, preauth_id=f"pp_mock_{dossier_id}", amount_cents=amount_cents)
