"""
Envoi de SMS transactionnels.

Templates :
- client_link : lien sécurisé pour collecter les documents du client
- otp_cession : code OTP pour confirmer la signature de la cession

Backends :
- development : log seulement (pas d'envoi réel)
- production  : Twilio
"""
from __future__ import annotations

import logging

logger = logging.getLogger(__name__)


def build_sms_client_link(
    client_prenom: str | None,
    nom_commerce: str,
    lien: str,
    telephone_commerce: str,
    type_compte: str = "VENDEUR_HABILITE",
) -> str:
    """
    Construit le SMS personnalisé envoyé au client.
    ~250 caractères max (2 SMS).
    Adapté selon le type de compte du pro.
    """
    prenom_part = f" {client_prenom}" if client_prenom else ""
    if type_compte == "AGENT_HABILITE":
        intro = f"{nom_commerce} traite votre demande de carte grise."
    else:
        intro = f"{nom_commerce} a choisi AutoDoc Pro pour votre carte grise."
    return (
        f"Bonjour{prenom_part}, "
        f"{intro} "
        f"Deposez gratuitement vos documents ici : {lien} "
        f"Infos & confidentialite : cartegrisepro.fr/confidentialite — "
        f"Contact : {nom_commerce} au {telephone_commerce}"
    )


def build_sms_otp(code: str) -> str:
    """SMS contenant le code OTP pour la signature de cession."""
    return f"Votre code de confirmation pour la signature du certificat de cession : {code}. Ce code est valable 10 minutes."


def _get_twilio_client():
    """Initialise le client Twilio depuis les settings."""
    from config.settings import get_settings
    settings = get_settings()

    account_sid = getattr(settings, "twilio_account_sid", "")
    auth_token = getattr(settings, "twilio_auth_token", "")

    if not account_sid or not auth_token:
        raise RuntimeError(
            "Twilio non configure — definir TWILIO_ACCOUNT_SID et TWILIO_AUTH_TOKEN dans .env"
        )

    from twilio.rest import Client
    return Client(account_sid, auth_token)


async def send_sms(to: str, message: str) -> bool:
    """
    Envoie un SMS.

    En dev : log seulement.
    En prod : Twilio.
    """
    from config.settings import get_settings
    settings = get_settings()

    # Dev → log seulement
    if settings.app_env.value == "development":
        logger.info(f"[SMS DEV] To={to} Message={message[:120]}...")
        return True

    # Production → Twilio
    try:
        client = _get_twilio_client()
        from_number = getattr(settings, "twilio_phone_number", "")
        if not from_number:
            raise RuntimeError("TWILIO_PHONE_NUMBER non configure dans .env")

        msg = client.messages.create(
            body=message,
            from_=from_number,
            to=to,
        )
        logger.info(f"[SMS] Envoye sid={msg.sid} to={to}")
        return True
    except Exception as e:
        logger.error(f"[SMS] Echec envoi to={to} : {e}")
        return False
