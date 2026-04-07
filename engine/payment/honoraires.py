"""
Paiement des HONORAIRES — c'est l'argent du porteur de projet.

Pre-autorisation CB au moment du GO/NO-GO.
Debit uniquement sur dossiers aboutis (CPI genere).
Alternative : facture mensuelle + prelevement SEPA pour pros a volume.

Provider : Stripe (configurable).

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
    client_secret: str | None = None
    error: str | None = None
    amount_cents: int = 0


@dataclass
class CaptureResult:
    success: bool
    payment_id: str | None = None
    error: str | None = None
    amount_cents: int = 0


def _get_stripe():
    """Initialise et retourne le module stripe configure."""
    import stripe
    from config.settings import get_settings
    settings = get_settings()
    stripe.api_key = settings.stripe_secret_key
    if not stripe.api_key:
        raise RuntimeError("STRIPE_SECRET_KEY non configure dans .env")
    return stripe


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
        Valide 7 jours (Stripe).
        """
        logger.info(
            f"[Honoraires] Pre-auth {amount_cents/100:.2f} EUR "
            f"dossier={dossier_id} pro={professionnel_id}"
        )
        return await self._stripe_preauth(amount_cents, stripe_customer_id, dossier_id)

    async def capture(self, preauth_id: str, amount_cents: int | None = None) -> CaptureResult:
        """
        Debite le montant pre-autorise. Appele uniquement quand le CPI est genere.
        amount_cents optionnel pour debit partiel.
        """
        logger.info(f"[Honoraires] Capture preauth={preauth_id}")
        try:
            stripe = _get_stripe()
            params = {}
            if amount_cents is not None:
                params["amount_to_capture"] = amount_cents
            intent = stripe.PaymentIntent.capture(preauth_id, **params)
            return CaptureResult(
                success=True,
                payment_id=intent.id,
                amount_cents=intent.amount_received,
            )
        except Exception as e:
            logger.error(f"[Honoraires] Capture echouee : {e}")
            return CaptureResult(success=False, error=str(e))

    async def cancel_preauth(self, preauth_id: str) -> bool:
        """Annule la pre-autorisation (dossier annule ou rejete)."""
        logger.info(f"[Honoraires] Annulation preauth={preauth_id}")
        try:
            stripe = _get_stripe()
            stripe.PaymentIntent.cancel(preauth_id)
            return True
        except Exception as e:
            logger.error(f"[Honoraires] Annulation echouee : {e}")
            return False

    async def create_checkout_session(
        self,
        dossier_id: UUID,
        professionnel_id: UUID,
        amount_cents: int,
        success_url: str,
        cancel_url: str,
        stripe_customer_id: str | None = None,
    ) -> dict:
        """
        Cree une session Stripe Checkout pour paiement direct.
        Retourne l'URL de redirection.
        """
        stripe = _get_stripe()
        params = {
            "payment_method_types": ["card"],
            "mode": "payment",
            "line_items": [{
                "price_data": {
                    "currency": "eur",
                    "unit_amount": amount_cents,
                    "product_data": {
                        "name": "Honoraires dossier carte grise",
                        "description": f"Dossier {dossier_id}",
                    },
                },
                "quantity": 1,
            }],
            "metadata": {
                "dossier_id": str(dossier_id),
                "professionnel_id": str(professionnel_id),
            },
            "success_url": success_url,
            "cancel_url": cancel_url,
        }
        if stripe_customer_id:
            params["customer"] = stripe_customer_id

        session = stripe.checkout.Session.create(**params)
        logger.info(f"[Honoraires] Checkout session={session.id} dossier={dossier_id}")
        return {
            "session_id": session.id,
            "url": session.url,
        }

    async def create_monthly_invoice(
        self,
        professionnel_id: UUID,
        dossiers_aboutis: list[dict],
        tarif_unitaire_cents: int,
    ) -> dict:
        """
        Genere une facture mensuelle pour les pros en mode abonnement.
        """
        total = len(dossiers_aboutis) * tarif_unitaire_cents
        logger.info(
            f"[Honoraires] Facture mensuelle pro={professionnel_id} "
            f"{len(dossiers_aboutis)} dossiers x {tarif_unitaire_cents/100:.2f} EUR = {total/100:.2f} EUR"
        )
        stripe = _get_stripe()
        # Creer les invoice items puis la facture
        for d in dossiers_aboutis:
            stripe.InvoiceItem.create(
                customer=d.get("stripe_customer_id"),
                amount=tarif_unitaire_cents,
                currency="eur",
                description=f"Dossier {d.get('reference', '?')}",
            )
        invoice = stripe.Invoice.create(
            customer=dossiers_aboutis[0].get("stripe_customer_id"),
            auto_advance=True,  # Envoi auto + tentative de paiement
            metadata={"professionnel_id": str(professionnel_id)},
        )
        return {
            "professionnel_id": str(professionnel_id),
            "invoice_id": invoice.id,
            "nb_dossiers": len(dossiers_aboutis),
            "total_cents": total,
            "status": invoice.status,
        }

    # ─── Providers ────────────────────────────────────────────────────────

    async def _stripe_preauth(self, amount_cents, customer_id, dossier_id) -> PreauthResult:
        """Pre-auth via Stripe PaymentIntent (capture_method=manual)."""
        try:
            stripe = _get_stripe()
            params = {
                "amount": amount_cents,
                "currency": "eur",
                "capture_method": "manual",
                "metadata": {"dossier_id": str(dossier_id)},
            }
            if customer_id:
                params["customer"] = customer_id
            intent = stripe.PaymentIntent.create(**params)
            return PreauthResult(
                success=True,
                preauth_id=intent.id,
                client_secret=intent.client_secret,
                amount_cents=amount_cents,
            )
        except Exception as e:
            logger.error(f"[Honoraires] Stripe pre-auth echouee : {e}")
            return PreauthResult(success=False, error=str(e))
