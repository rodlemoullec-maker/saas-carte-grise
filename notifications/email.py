"""
Envoi d'emails transactionnels via SMTP async.

Templates :
- dossier_recu          → confirmation réception dossier
- documents_manquants   → liste des docs manquants + relance
- correction_requise    → liste des corrections à apporter
- dossier_accepte       → dossier validé, GO possible
- dossier_rejete        → rejet avec motif
- siv_confirme          → CG envoyée, CPI disponible
- phase0_alerte         → blocage détecté en Phase 0 (gage/vol/OTCI)
- client_a_uploade      → notification pro quand client dépose docs
- cerfa_pret            → notification pro quand Cerfa est prêt

Backends :
- development : log seulement
- production  : SMTP async (aiosmtplib)
"""
from __future__ import annotations

import logging
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Any

logger = logging.getLogger(__name__)


# Templates (clé → sujet + corps)
TEMPLATES: dict[str, dict[str, str]] = {
    "dossier_recu": {
        "subject": "Votre dossier {reference} a été reçu",
        "body": (
            "Bonjour {client_nom},\n\n"
            "Votre dossier de carte grise {reference} a bien été créé.\n"
            "Nous traitons vos documents et reviendrons vers vous rapidement.\n\n"
            "Référence : {reference}\n"
            "Type : {type}\n\n"
            "Cordialement,\nL'équipe AutoDoc Pro"
        ),
    },
    "documents_manquants": {
        "subject": "[Action requise] Documents manquants — Dossier {reference}",
        "body": (
            "Bonjour {client_nom},\n\n"
            "Il nous manque les documents suivants pour traiter votre dossier {reference} :\n\n"
            "{documents_list}\n\n"
            "Merci de les transmettre au plus vite à votre professionnel.\n\n"
            "Cordialement,\nL'équipe AutoDoc Pro"
        ),
    },
    "correction_requise": {
        "subject": "[Action requise] Corrections nécessaires — Dossier {reference}",
        "body": (
            "Bonjour,\n\n"
            "Le dossier {reference} nécessite des corrections :\n\n"
            "{corrections_list}\n\n"
            "Merci de corriger ces points et de relancer le traitement.\n\n"
            "Cordialement,\nL'équipe AutoDoc Pro"
        ),
    },
    "dossier_accepte": {
        "subject": "Dossier {reference} validé — Prêt pour le traitement",
        "body": (
            "Bonjour,\n\n"
            "Le dossier {reference} a passé tous les contrôles.\n"
            "Diagnostic : {diagnostic}\n\n"
            "Estimation taxes : {tax_total} EUR (indicatif)\n\n"
            "Vous pouvez generer le Cerfa depuis votre espace.\n\n"
            "Cordialement,\nL'équipe AutoDoc Pro"
        ),
    },
    "dossier_rejete": {
        "subject": "Dossier {reference} — Rejet",
        "body": (
            "Bonjour,\n\n"
            "Le dossier {reference} a été rejeté.\n\n"
            "Motif(s) :\n{motifs}\n\n"
            "Contactez-nous si vous pensez qu'il s'agit d'une erreur.\n\n"
            "Cordialement,\nL'équipe AutoDoc Pro"
        ),
    },
    "siv_confirme": {
        "subject": "Carte grise envoyée — Dossier {reference}",
        "body": (
            "Bonjour {client_nom},\n\n"
            "Votre demande de carte grise a été soumise au SIV.\n"
            "Référence SIV : {siv_reference}\n\n"
            "Le Certificat Provisoire d'Immatriculation (CPI) est disponible.\n\n"
            "Cordialement,\nL'équipe AutoDoc Pro"
        ),
    },
    "docs_pro_qualite": {
        "subject": "[Action requise] Document illisible — Dossier {reference}",
        "body": (
            "Bonjour,\n\n"
            "Un ou plusieurs documents que vous avez déposés pour le dossier {reference} "
            "n'ont pas pu être lus correctement par notre système :\n\n"
            "{problemes_list}\n\n"
            "Merci de re-déposer les documents concernés depuis votre espace.\n\n"
            "Conseils :\n"
            "- Scanner le document bien à plat, avec un bon éclairage\n"
            "- Éviter les reflets, les doigts sur le document, les zones d'ombre\n"
            "- Privilégier le format PDF ou une photo nette en haute résolution\n\n"
            "Cordialement,\nL'équipe AutoDoc Pro"
        ),
    },
    "docs_pro_valides": {
        "subject": "Documents validés — Lien envoyé au client — Dossier {reference}",
        "body": (
            "Bonjour,\n\n"
            "Vos documents pour le dossier {reference} ont été validés avec succès.\n\n"
            "Documents traités :\n{documents_ok_list}\n\n"
            "Le lien de collecte a été envoyé automatiquement à votre client "
            "au {client_telephone}.\n\n"
            "Vous serez notifié dès que le client aura déposé ses documents.\n\n"
            "Cordialement,\nL'équipe AutoDoc Pro"
        ),
    },
    "phase0_alerte": {
        "subject": "[ALERTE] Blocage détecté sur le véhicule — {immatriculation}",
        "body": (
            "Bonjour,\n\n"
            "Le pré-diagnostic Phase 0 a détecté un blocage sur le véhicule "
            "{immatriculation} :\n\n"
            "{blockers}\n\n"
            "Le dossier ne peut pas être poursuivi tant que ce blocage n'est pas levé.\n\n"
            "Cordialement,\nL'équipe AutoDoc Pro"
        ),
    },
    "client_a_uploade": {
        "subject": "Votre client a déposé ses documents — Dossier {reference}",
        "body": (
            "Bonjour,\n\n"
            "Votre client {client_nom} a déposé ses documents pour le dossier {reference}.\n\n"
            "Documents reçus :\n{documents_list}\n\n"
            "Connectez-vous à votre espace pour lancer le diagnostic.\n\n"
            "Cordialement,\nL'équipe AutoDoc Pro"
        ),
    },
    "cerfa_pret": {
        "subject": "Cerfa prêt — Dossier {reference}",
        "body": (
            "Bonjour,\n\n"
            "Le Cerfa du dossier {reference} est prêt.\n\n"
            "Connectez-vous à votre espace pour le télécharger et le soumettre au SIV.\n\n"
            "Cordialement,\nL'équipe AutoDoc Pro"
        ),
    },
}


async def send_email(to: str, template: str, context: dict[str, Any]) -> bool:
    """
    Envoie un email transactionnel.

    En dev : log seulement.
    En prod : SMTP async via aiosmtplib.
    """
    tpl = TEMPLATES.get(template)
    if not tpl:
        logger.error(f"Template email inconnu : {template}")
        return False

    subject = tpl["subject"].format_map(_safe_context(context))
    body = tpl["body"].format_map(_safe_context(context))

    from config.settings import get_settings
    settings = get_settings()

    # Dev → log seulement
    if settings.app_env.value == "development":
        logger.info(f"[Email DEV] To={to} Subject={subject}")
        return True

    # Production → SMTP
    try:
        import aiosmtplib

        msg = MIMEMultipart()
        msg["From"] = f"AutoDoc Pro <{settings.smtp_from_email}>"
        msg["To"] = to
        msg["Subject"] = subject
        msg.attach(MIMEText(body, "plain", "utf-8"))

        await aiosmtplib.send(
            msg,
            hostname=settings.smtp_host,
            port=settings.smtp_port,
            username=settings.smtp_user,
            password=settings.smtp_password,
            start_tls=True,
        )
        logger.info(f"[Email] Envoye to={to} subject={subject[:50]}")
        return True
    except Exception as e:
        logger.error(f"[Email] Echec envoi a {to}: {e}")
        return False


async def send_relance(
    dossier_reference: str,
    client_email: str | None,
    pro_email: str,
    relance_mode: str,
    template: str,
    context: dict[str, Any],
) -> bool:
    """
    Envoie une relance selon le mode choisi par le pro.

    relance_mode = "SYSTEME" → email au client directement
    relance_mode = "PRO" → email au pro qui relaiera
    """
    if relance_mode == "SYSTEME" and client_email:
        return await send_email(client_email, template, context)
    else:
        context["_note_relance"] = "À transmettre à votre client"
        return await send_email(pro_email, template, context)


def _safe_context(context: dict) -> dict:
    """Retourne un dict qui ne raise pas sur les clés manquantes."""

    class SafeDict(dict):
        def __missing__(self, key):
            return f"[{key}]"

    return SafeDict(context)
