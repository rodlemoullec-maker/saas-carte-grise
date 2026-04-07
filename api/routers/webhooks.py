"""
Router webhooks — callbacks entrants Stripe + SIV ANTS.
"""
from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import Depends

from api.models.base import get_db
from api.models.dossier import DossierDB

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/stripe")
async def stripe_webhook(request: Request, db: AsyncSession = Depends(get_db)):
    """
    Webhook Stripe — confirme les paiements.
    Evenements geres :
      - checkout.session.completed → marquer le dossier comme paye
      - payment_intent.succeeded  → capturer la pre-auth
    """
    import stripe
    from config.settings import get_settings
    settings = get_settings()

    payload = await request.body()
    sig_header = request.headers.get("stripe-signature", "")

    if not settings.stripe_webhook_secret:
        logger.error("[Webhook Stripe] STRIPE_WEBHOOK_SECRET non configure")
        raise HTTPException(500, "Webhook secret non configure")

    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, settings.stripe_webhook_secret
        )
    except stripe.error.SignatureVerificationError:
        logger.warning("[Webhook Stripe] Signature invalide")
        raise HTTPException(400, "Signature invalide")
    except Exception as e:
        logger.error(f"[Webhook Stripe] Erreur parsing : {e}")
        raise HTTPException(400, str(e))

    event_type = event["type"]
    data = event["data"]["object"]
    logger.info(f"[Webhook Stripe] {event_type} id={data.get('id')}")

    if event_type == "checkout.session.completed":
        dossier_id = (data.get("metadata") or {}).get("dossier_id")
        if dossier_id:
            dossier = await db.get(DossierDB, dossier_id)
            if dossier:
                dossier.payment_captured = True
                dossier.payment_preauth_id = data.get("payment_intent")
                await db.flush()
                logger.info(f"[Webhook Stripe] Paiement confirme dossier={dossier_id}")

    elif event_type == "payment_intent.succeeded":
        dossier_id = (data.get("metadata") or {}).get("dossier_id")
        if dossier_id:
            dossier = await db.get(DossierDB, dossier_id)
            if dossier:
                dossier.payment_captured = True
                await db.flush()
                logger.info(f"[Webhook Stripe] PaymentIntent captured dossier={dossier_id}")

    return {"status": "ok"}


@router.post("/siv/status")
async def siv_status_callback(request: Request):
    # TODO: verifier signature webhook + parser payload + MAJ statut + notifier
    raise NotImplementedError
