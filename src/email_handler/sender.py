"""Envoi d'emails — Accusés réception, relances, envoi CERFA.

Utilise smtplib (stdlib) pour envoyer des emails via SMTP.
"""

import smtplib
from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path

from config.settings import IMAP_SERVER, IMAP_USER, IMAP_PASSWORD


# Templates d'emails
TEMPLATES = {
    "accuse_reception": {
        "subject": "Votre dossier carte grise {reference} a été reçu",
        "body": """Bonjour,

Nous avons bien reçu votre demande de carte grise (référence : {reference}).

Documents reçus : {nb_fichiers} pièce(s) jointe(s).

Votre dossier est en cours de traitement. Nous reviendrons vers vous rapidement.

Cordialement,
Service Carte Grise""",
    },
    "relance_documents": {
        "subject": "Dossier {reference} — Documents manquants",
        "body": """Bonjour,

Votre dossier carte grise (référence : {reference}) est incomplet.

Document(s) manquant(s) :
{documents_manquants}

Merci de nous transmettre ces documents par retour de mail afin que nous puissions finaliser le traitement.

Cordialement,
Service Carte Grise""",
    },
    "dossier_pret": {
        "subject": "Dossier {reference} — CERFA prêt",
        "body": """Bonjour,

Le dossier carte grise (référence : {reference}) a été traité avec succès.

--- Récapitulatif du traitement ---

Véhicule : {marque} {denomination} — {immatriculation}

Actions effectuées par le système :
1. Réception et identification de {nb_documents} document(s)
2. Extraction automatique des données par OCR et intelligence artificielle
3. Vérification de cohérence entre les documents (VIN, identité, dates)
4. Recherche des caractéristiques techniques du véhicule dans la base de données
5. Calcul des taxes carte grise selon la réglementation en vigueur
6. Pré-remplissage du formulaire CERFA 13750

Résultat des vérifications :
{verifications}

--- Pièce jointe ---

Vous trouverez en pièce jointe le CERFA 13750 pré-rempli.
Merci de vérifier les informations avant soumission auprès de l'ANTS.

Si vous constatez une erreur, merci de nous le signaler par retour de mail.

Cordialement,
Service Carte Grise""",
    },
    "erreur_validation": {
        "subject": "Dossier {reference} — Incohérences détectées",
        "body": """Bonjour,

Le dossier carte grise (référence : {reference}) présente des incohérences :

{erreurs}

Merci de vérifier les documents et de nous les renvoyer corrigés.

Cordialement,
Service Carte Grise""",
    },
}


class EmailSender:
    """Envoi d'emails via SMTP."""

    def __init__(
        self,
        smtp_server: str = "",
        smtp_port: int = 587,
        user: str = "",
        password: str = "",
    ):
        # Déduire le serveur SMTP depuis le serveur IMAP
        self.smtp_server = smtp_server or _imap_to_smtp(IMAP_SERVER)
        self.smtp_port = smtp_port
        self.user = user or IMAP_USER
        self.password = password or IMAP_PASSWORD

    def send(
        self,
        to: str,
        subject: str,
        body: str,
        attachments: list[str | Path] | None = None,
    ) -> bool:
        """Envoie un email.

        Args:
            to: Adresse du destinataire.
            subject: Sujet de l'email.
            body: Corps du message (texte brut).
            attachments: Liste de chemins vers les fichiers à joindre.

        Returns:
            True si envoyé avec succès.
        """
        if not self.smtp_server or not self.user:
            raise ValueError("SMTP non configuré. Vérifiez .env")

        msg = MIMEMultipart()
        msg["From"] = self.user
        msg["To"] = to
        msg["Subject"] = subject

        msg.attach(MIMEText(body, "plain", "utf-8"))

        # Ajouter les pièces jointes
        if attachments:
            for filepath in attachments:
                filepath = Path(filepath)
                if not filepath.exists():
                    continue
                with open(filepath, "rb") as f:
                    part = MIMEApplication(f.read(), Name=filepath.name)
                part["Content-Disposition"] = f'attachment; filename="{filepath.name}"'
                msg.attach(part)

        # Envoi
        with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
            server.starttls()
            server.login(self.user, self.password)
            server.send_message(msg)

        return True

    def send_accuse_reception(self, to: str, reference: str, nb_fichiers: int) -> bool:
        """Envoie un accusé de réception."""
        tmpl = TEMPLATES["accuse_reception"]
        return self.send(
            to=to,
            subject=tmpl["subject"].format(reference=reference),
            body=tmpl["body"].format(reference=reference, nb_fichiers=nb_fichiers),
        )

    def send_relance_documents(
        self, to: str, reference: str, documents_manquants: list[str]
    ) -> bool:
        """Envoie une relance pour documents manquants."""
        tmpl = TEMPLATES["relance_documents"]
        docs_list = "\n".join(f"  - {doc}" for doc in documents_manquants)
        return self.send(
            to=to,
            subject=tmpl["subject"].format(reference=reference),
            body=tmpl["body"].format(
                reference=reference, documents_manquants=docs_list
            ),
        )

    def send_cerfa(
        self,
        to: str,
        reference: str,
        cerfa_path: str | Path,
        marque: str = "",
        denomination: str = "",
        immatriculation: str = "",
        nb_documents: int = 0,
        verifications: str = "",
    ) -> bool:
        """Envoie le CERFA pré-rempli à la personne habilitée avec récapitulatif."""
        tmpl = TEMPLATES["dossier_pret"]

        if not verifications:
            verifications = "- Toutes les vérifications ont été passées avec succès"

        return self.send(
            to=to,
            subject=tmpl["subject"].format(reference=reference),
            body=tmpl["body"].format(
                reference=reference,
                marque=marque,
                denomination=denomination,
                immatriculation=immatriculation,
                nb_documents=nb_documents,
                verifications=verifications,
            ),
            attachments=[cerfa_path],
        )

    def send_erreur_validation(
        self, to: str, reference: str, erreurs: list[str]
    ) -> bool:
        """Envoie une notification d'erreurs de validation."""
        tmpl = TEMPLATES["erreur_validation"]
        erreurs_list = "\n".join(f"  - {e}" for e in erreurs)
        return self.send(
            to=to,
            subject=tmpl["subject"].format(reference=reference),
            body=tmpl["body"].format(reference=reference, erreurs=erreurs_list),
        )


def _imap_to_smtp(imap_server: str) -> str:
    """Déduit le serveur SMTP depuis le serveur IMAP."""
    if not imap_server:
        return ""
    return imap_server.replace("imap.", "smtp.")
