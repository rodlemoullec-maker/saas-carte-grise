"""Réception email — Polling IMAP + extraction pièces jointes.

Se connecte à la boîte mail via IMAP, détecte les nouveaux emails
avec pièces jointes, et crée un dossier par demande.
"""

import email
import imaplib
import os
import re
from datetime import datetime
from email.header import decode_header
from pathlib import Path

from config.settings import (
    IMAP_SERVER,
    IMAP_PORT,
    IMAP_USER,
    IMAP_PASSWORD,
    DOSSIERS_DIR,
)


class EmailReceiver:
    """Récepteur d'emails IMAP pour les demandes de carte grise."""

    SUPPORTED_EXTENSIONS = {".pdf", ".jpg", ".jpeg", ".png", ".tif", ".tiff", ".bmp"}

    def __init__(
        self,
        server: str = "",
        port: int = 993,
        user: str = "",
        password: str = "",
    ):
        self.server = server or IMAP_SERVER
        self.port = port or IMAP_PORT
        self.user = user or IMAP_USER
        self.password = password or IMAP_PASSWORD
        self._connection = None

    def connect(self) -> None:
        """Établit la connexion IMAP."""
        if not self.server or not self.user:
            raise ValueError("IMAP_SERVER et IMAP_USER doivent être configurés dans .env")

        self._connection = imaplib.IMAP4_SSL(self.server, self.port)
        self._connection.login(self.user, self.password)
        self._connection.select("INBOX")

    def disconnect(self) -> None:
        """Ferme la connexion IMAP."""
        if self._connection:
            try:
                self._connection.close()
                self._connection.logout()
            except Exception:
                pass
            self._connection = None

    def fetch_new_emails(self) -> list[dict]:
        """Récupère les emails non lus avec pièces jointes.

        Returns:
            Liste de dicts avec :
            - email_id: ID de l'email
            - sender: adresse de l'expéditeur
            - subject: sujet de l'email
            - date: date de réception
            - attachments: liste de dicts {filename, content, content_type}
        """
        if not self._connection:
            self.connect()

        # Chercher les emails non lus
        status, messages = self._connection.search(None, "UNSEEN")
        if status != "OK" or not messages[0]:
            return []

        email_ids = messages[0].split()
        results = []

        for email_id in email_ids:
            status, msg_data = self._connection.fetch(email_id, "(RFC822)")
            if status != "OK":
                continue

            raw_email = msg_data[0][1]
            msg = email.message_from_bytes(raw_email)

            sender = self._decode_header(msg.get("From", ""))
            subject = self._decode_header(msg.get("Subject", ""))
            date_str = msg.get("Date", "")

            # Extraire l'adresse email de l'expéditeur
            sender_email = self._extract_email(sender)

            # Extraire les pièces jointes
            attachments = self._extract_attachments(msg)

            if attachments:  # On ne garde que les emails avec PJ
                results.append({
                    "email_id": email_id.decode(),
                    "sender": sender,
                    "sender_email": sender_email,
                    "subject": subject,
                    "date": date_str,
                    "attachments": attachments,
                })

        return results

    def save_dossier(self, email_data: dict) -> dict:
        """Sauvegarde les PJ d'un email dans un dossier dédié.

        Crée un répertoire par dossier : data/dossiers/{reference}/

        Args:
            email_data: Dict retourné par fetch_new_emails().

        Returns:
            Dict avec reference, dossier_path, fichiers sauvegardés.
        """
        # Générer une référence unique
        now = datetime.now()
        reference = f"CG-{now.strftime('%Y%m%d-%H%M%S')}"

        dossier_path = DOSSIERS_DIR / reference
        dossier_path.mkdir(parents=True, exist_ok=True)

        saved_files = []
        for att in email_data.get("attachments", []):
            filename = self._sanitize_filename(att["filename"])
            filepath = dossier_path / filename

            # Éviter les doublons
            counter = 1
            while filepath.exists():
                stem = filepath.stem
                suffix = filepath.suffix
                filepath = dossier_path / f"{stem}_{counter}{suffix}"
                counter += 1

            with open(filepath, "wb") as f:
                f.write(att["content"])

            saved_files.append({
                "filename": filename,
                "path": str(filepath),
                "content_type": att.get("content_type", ""),
                "size": len(att["content"]),
            })

        return {
            "reference": reference,
            "dossier_path": str(dossier_path),
            "sender": email_data.get("sender", ""),
            "sender_email": email_data.get("sender_email", ""),
            "subject": email_data.get("subject", ""),
            "date": email_data.get("date", ""),
            "fichiers": saved_files,
            "nb_fichiers": len(saved_files),
        }

    def mark_as_read(self, email_id: str) -> None:
        """Marque un email comme lu."""
        if self._connection:
            self._connection.store(email_id.encode(), "+FLAGS", "\\Seen")

    def _extract_attachments(self, msg: email.message.Message) -> list[dict]:
        """Extrait les pièces jointes d'un email."""
        attachments = []

        for part in msg.walk():
            content_disposition = str(part.get("Content-Disposition", ""))
            if "attachment" not in content_disposition and "inline" not in content_disposition:
                continue

            filename = part.get_filename()
            if not filename:
                continue

            filename = self._decode_header(filename)
            ext = Path(filename).suffix.lower()

            if ext not in self.SUPPORTED_EXTENSIONS:
                continue

            content = part.get_payload(decode=True)
            if content:
                attachments.append({
                    "filename": filename,
                    "content": content,
                    "content_type": part.get_content_type(),
                })

        return attachments

    @staticmethod
    def _decode_header(value: str) -> str:
        """Décode un en-tête email (gestion encodages)."""
        if not value:
            return ""
        decoded_parts = decode_header(value)
        result = []
        for part, charset in decoded_parts:
            if isinstance(part, bytes):
                result.append(part.decode(charset or "utf-8", errors="replace"))
            else:
                result.append(part)
        return " ".join(result)

    @staticmethod
    def _extract_email(sender: str) -> str:
        """Extrait l'adresse email d'un champ From."""
        match = re.search(r"<(.+?)>", sender)
        if match:
            return match.group(1).lower()
        if "@" in sender:
            return sender.strip().lower()
        return sender

    @staticmethod
    def _sanitize_filename(filename: str) -> str:
        """Nettoie un nom de fichier."""
        # Retirer les caractères dangereux
        filename = re.sub(r'[<>:"/\\|?*]', "_", filename)
        filename = filename.strip(". ")
        return filename or "document"
