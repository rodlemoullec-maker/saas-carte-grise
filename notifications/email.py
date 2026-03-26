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

Architecture : SMTP async (aiosmtplib) en dev, SendGrid en production.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class EmailConfig:
    smtp_host: str = "localhost"
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""
    from_email: str = "noreply@cartegrise.pro"
    from_name: str = "Carte Grise Pro"


# Templates (clé → sujet + corps simplifié)
# En production, utiliser Jinja2 avec templates HTML
TEMPLATES: dict[str, dict[str, str]] = {
    "dossier_recu": {
        "subject": "Votre dossier {reference} a été reçu",
        "body": (
            "Bonjour {client_nom},\n\n"
            "Votre dossier de carte grise {reference} a bien été créé.\n"
            "Nous traitons vos documents et reviendrons vers vous rapidement.\n\n"
            "Référence : {reference}\n"
            "Type : {type}\n\n"
            "Cordialement,\nL'équipe Carte Grise Pro"
        ),
    },
    "documents_manquants": {
        "subject": "[Action requise] Documents manquants — Dossier {reference}",
        "body": (
            "Bonjour {client_nom},\n\n"
            "Il nous manque les documents suivants pour traiter votre dossier {reference} :\n\n"
            "{documents_list}\n\n"
            "Merci de les transmettre au plus vite à votre professionnel.\n\n"
            "Cordialement,\nL'équipe Carte Grise Pro"
        ),
    },
    "correction_requise": {
        "subject": "[Action requise] Corrections nécessaires — Dossier {reference}",
        "body": (
            "Bonjour,\n\n"
            "Le dossier {reference} nécessite des corrections :\n\n"
            "{corrections_list}\n\n"
            "Merci de corriger ces points et de relancer le traitement.\n\n"
            "Cordialement,\nL'équipe Carte Grise Pro"
        ),
    },
    "dossier_accepte": {
        "subject": "Dossier {reference} validé — Prêt pour le traitement",
        "body": (
            "Bonjour,\n\n"
            "Le dossier {reference} a passé tous les contrôles.\n"
            "Diagnostic : {diagnostic}\n"
            "Score : {score}/100\n\n"
            "Estimation taxes : {tax_total}€ (indicatif)\n\n"
            "Vous pouvez lancer le traitement depuis votre espace.\n\n"
            "Cordialement,\nL'équipe Carte Grise Pro"
        ),
    },
    "dossier_rejete": {
        "subject": "Dossier {reference} — Rejet",
        "body": (
            "Bonjour,\n\n"
            "Le dossier {reference} a été rejeté.\n\n"
            "Motif(s) :\n{motifs}\n\n"
            "Contactez-nous si vous pensez qu'il s'agit d'une erreur.\n\n"
            "Cordialement,\nL'équipe Carte Grise Pro"
        ),
    },
    "siv_confirme": {
        "subject": "Carte grise envoyée — Dossier {reference}",
        "body": (
            "Bonjour {client_nom},\n\n"
            "Votre demande de carte grise a été soumise au SIV.\n"
            "Référence SIV : {siv_reference}\n\n"
            "Le Certificat Provisoire d'Immatriculation (CPI) est disponible.\n\n"
            "Cordialement,\nL'équipe Carte Grise Pro"
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
            "Cordialement,\nL'équipe Carte Grise Pro"
        ),
    },
}


async def send_email(to: str, template: str, context: dict[str, Any]) -> bool:
    """
    Envoie un email transactionnel.

    Args:
        to: Adresse email du destinataire
        template: Clé du template (voir TEMPLATES)
        context: Variables de contexte pour le template

    Returns:
        True si envoyé avec succès, False sinon.
    """
    tpl = TEMPLATES.get(template)
    if not tpl:
        logger.error(f"Template email inconnu : {template}")
        return False

    subject = tpl["subject"].format_map(_safe_context(context))
    body = tpl["body"].format_map(_safe_context(context))

    # TODO: en production, remplacer par aiosmtplib ou SendGrid
    logger.info(f"[Email] To={to} Subject={subject}")
    logger.debug(f"[Email] Body={body[:200]}...")

    # Placeholder — en dev, on log seulement
    try:
        # import aiosmtplib
        # await aiosmtplib.send(
        #     message=_build_mime(to, subject, body),
        #     hostname=config.smtp_host,
        #     port=config.smtp_port,
        #     username=config.smtp_user,
        #     password=config.smtp_password,
        #     start_tls=True,
        # )
        return True
    except Exception as e:
        logger.error(f"[Email] Échec envoi à {to}: {e}")
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
