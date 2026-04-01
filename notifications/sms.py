"""
Envoi de SMS transactionnels.

Templates :
- client_link : lien sécurisé pour collecter les documents du client
- otp_cession : code OTP pour confirmer la signature de la cession

TODO: implémenter avec Twilio ou OVH SMS en production.
"""
from __future__ import annotations

import logging

logger = logging.getLogger(__name__)


def build_sms_client_link(
    client_prenom: str | None,
    nom_commerce: str,
    lien: str,
    telephone_commerce: str,
) -> str:
    """
    Construit le SMS personnalisé envoyé au client.
    ~250 caractères max (2 SMS).
    """
    prenom_part = f" {client_prenom}" if client_prenom else ""
    return (
        f"Bonjour{prenom_part}, "
        f"{nom_commerce} a choisi AutoDoc Pro pour votre carte grise. "
        f"Deposez gratuitement vos documents ici : {lien} "
        f"Infos & confidentialite : cartegrisepro.fr/confidentialite — "
        f"Contact : {nom_commerce} au {telephone_commerce}"
    )


def build_sms_otp(code: str) -> str:
    """SMS contenant le code OTP pour la signature de cession."""
    return f"Votre code de confirmation pour la signature du certificat de cession : {code}. Ce code est valable 10 minutes."


async def send_sms(to: str, message: str) -> bool:
    """
    Envoie un SMS.

    En dev : log seulement.
    En prod : Twilio ou OVH SMS.
    """
    logger.info(f"[SMS] To={to} Message={message[:100]}...")

    # TODO: en production, remplacer par l'appel Twilio/OVH
    # from twilio.rest import Client
    # client = Client(account_sid, auth_token)
    # client.messages.create(body=message, from_="+33...", to=to)

    return True
