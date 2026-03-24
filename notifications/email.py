"""
Envoi d'emails transactionnels.

Templates :
- dossier_recu          → confirmation réception dossier
- correction_requise    → liste des corrections à apporter
- dossier_accepte       → dossier validé, CG en cours
- dossier_rejete        → rejet avec motif
- siv_confirme          → CG envoyée

TODO: implémenter avec SMTP (smtplib async) ou SendGrid.
TODO: créer les templates HTML (Jinja2).
"""
from __future__ import annotations

async def send_email(to: str, subject: str, template: str, context: dict) -> None:
    raise NotImplementedError
