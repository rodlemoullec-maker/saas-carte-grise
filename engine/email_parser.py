"""
Parser d'emails — extraction des métadonnées et pièces jointes.

Supporte deux formats :
- .eml : format MIME standard (Gmail, Apple Mail, Thunderbird, exports IMAP)
- .msg : format Outlook propriétaire (via le package `extract-msg`)

Le parser est conçu pour être tolérant aux emails malformés ou aux formats
inhabituels — on préfère retourner ce qu'on peut extraire plutôt que de
lever une exception.

Usage :
    from engine.email_parser import parse_email_bytes

    parsed = parse_email_bytes(file_bytes, filename="email.eml")
    print(parsed.sender_email)
    for att in parsed.attachments:
        print(att.filename, att.size_bytes, att.mime_type)
"""
from __future__ import annotations

import logging
import mimetypes
import re
from dataclasses import dataclass, field
from email import message_from_bytes, policy
from email.message import EmailMessage
from email.utils import parseaddr

logger = logging.getLogger(__name__)


# ─── Configuration ──────────────────────────────────────────────────────────

# Types MIME des pièces jointes que l'on accepte de transmettre au pipeline OCR.
# Les autres (text/html, signatures, vcards, etc.) sont ignorées.
ACCEPTED_ATTACHMENT_MIME = {
    "application/pdf",
    "image/jpeg",
    "image/jpg",
    "image/png",
    "image/tiff",
    "image/tif",
    "image/webp",
}

# Extensions à ignorer dans les pièces jointes (parasites Outlook, signatures,
# images intégrées dans le corps HTML, etc.)
IGNORED_EXTENSIONS = {
    ".html",
    ".htm",
    ".vcf",
    ".ics",
    ".asc",  # signature PGP
    ".p7s",  # signature S/MIME
    ".smime",
    ".eml",  # email imbriqué (cas rare)
}

# Noms de fichiers parasites courants
IGNORED_FILENAMES = {
    "image001.png",
    "image002.png",
    "image003.png",
    "smime.p7s",
    "ATT00001.txt",
    "winmail.dat",
}


# ─── Modèles de données ────────────────────────────────────────────────────


@dataclass
class EmailAttachment:
    """Pièce jointe extraite d'un email."""
    filename: str
    content_bytes: bytes
    mime_type: str
    size_bytes: int

    @property
    def is_processable(self) -> bool:
        """True si le pipeline OCR peut traiter cette pièce."""
        return (
            self.mime_type in ACCEPTED_ATTACHMENT_MIME
            and self.filename not in IGNORED_FILENAMES
            and not any(self.filename.lower().endswith(ext) for ext in IGNORED_EXTENSIONS)
        )


@dataclass
class ParsedEmail:
    """Résultat du parsing d'un email — métadonnées + pièces jointes."""
    sender_name: str = ""
    sender_email: str = ""
    subject: str = ""
    body_text: str = ""
    body_html: str = ""
    date: str = ""
    attachments: list[EmailAttachment] = field(default_factory=list)
    format: str = ""  # "eml" ou "msg"

    @property
    def processable_attachments(self) -> list[EmailAttachment]:
        """Pièces jointes que le pipeline OCR peut traiter."""
        return [a for a in self.attachments if a.is_processable]


# ─── Parser .eml (format standard MIME) ────────────────────────────────────


def _parse_eml(file_bytes: bytes) -> ParsedEmail:
    """Parse un email au format .eml standard (RFC 5322 / MIME)."""
    msg: EmailMessage = message_from_bytes(file_bytes, policy=policy.default)  # type: ignore

    # Métadonnées
    sender_raw = msg.get("From", "")
    sender_name, sender_email = parseaddr(sender_raw)

    parsed = ParsedEmail(
        sender_name=sender_name or "",
        sender_email=sender_email or "",
        subject=msg.get("Subject", "") or "",
        date=msg.get("Date", "") or "",
        format="eml",
    )

    # Corps du message (texte et HTML)
    try:
        body_part = msg.get_body(preferencelist=("plain", "html"))
        if body_part is not None:
            content = body_part.get_content()
            if body_part.get_content_type() == "text/plain":
                parsed.body_text = content if isinstance(content, str) else ""
            else:
                parsed.body_html = content if isinstance(content, str) else ""
    except Exception as e:
        logger.debug(f"[email_parser] body extraction failed: {e}")

    # Pièces jointes
    try:
        for part in msg.iter_attachments():
            try:
                filename = part.get_filename() or "attachment.bin"
                content = part.get_content()
                if isinstance(content, str):
                    content = content.encode("utf-8", errors="replace")
                if not isinstance(content, (bytes, bytearray)):
                    continue
                content_bytes = bytes(content)
                mime_type = part.get_content_type() or _guess_mime(filename)

                parsed.attachments.append(
                    EmailAttachment(
                        filename=filename,
                        content_bytes=content_bytes,
                        mime_type=mime_type,
                        size_bytes=len(content_bytes),
                    )
                )
            except Exception as e:
                logger.warning(f"[email_parser] attachment skipped: {e}")
    except AttributeError:
        # Vieux format — fallback walk()
        for part in msg.walk():
            if part.get_content_disposition() == "attachment":
                try:
                    filename = part.get_filename() or "attachment.bin"
                    payload = part.get_payload(decode=True)
                    if not payload:
                        continue
                    parsed.attachments.append(
                        EmailAttachment(
                            filename=filename,
                            content_bytes=payload,
                            mime_type=part.get_content_type() or _guess_mime(filename),
                            size_bytes=len(payload),
                        )
                    )
                except Exception as e:
                    logger.warning(f"[email_parser] walk attachment skipped: {e}")

    return parsed


# ─── Parser .msg (format Outlook propriétaire) ─────────────────────────────


def _parse_msg(file_bytes: bytes) -> ParsedEmail:
    """
    Parse un email au format .msg Outlook via extract-msg.

    Note : extract-msg attend un fichier sur disque, on passe par un
    fichier temporaire car le module ne gère pas BytesIO directement.
    """
    try:
        import extract_msg
    except ImportError as e:
        raise ImportError(
            "Le format .msg nécessite le package `extract-msg`. "
            "Installez avec : pip install extract-msg"
        ) from e

    import os
    import tempfile

    with tempfile.NamedTemporaryFile(suffix=".msg", delete=False) as tmp:
        tmp.write(file_bytes)
        tmp_path = tmp.name

    try:
        msg = extract_msg.Message(tmp_path)

        sender_raw = (msg.sender or "") if hasattr(msg, "sender") else ""
        sender_name, sender_email = parseaddr(sender_raw)
        # extract-msg expose parfois sender_email directement
        if not sender_email and hasattr(msg, "senderEmail"):
            sender_email = msg.senderEmail or ""

        parsed = ParsedEmail(
            sender_name=sender_name or "",
            sender_email=sender_email or "",
            subject=(msg.subject or "") if hasattr(msg, "subject") else "",
            body_text=(msg.body or "") if hasattr(msg, "body") else "",
            body_html=(msg.htmlBody or "") if hasattr(msg, "htmlBody") else "",
            date=str(msg.date) if hasattr(msg, "date") and msg.date else "",
            format="msg",
        )

        # Pièces jointes
        for att in (msg.attachments or []):
            try:
                filename = (
                    getattr(att, "longFilename", None)
                    or getattr(att, "shortFilename", None)
                    or "attachment.bin"
                )
                content_bytes = getattr(att, "data", None) or b""
                if not content_bytes:
                    continue
                mime_type = _guess_mime(filename)

                parsed.attachments.append(
                    EmailAttachment(
                        filename=filename,
                        content_bytes=content_bytes,
                        mime_type=mime_type,
                        size_bytes=len(content_bytes),
                    )
                )
            except Exception as e:
                logger.warning(f"[email_parser] msg attachment skipped: {e}")

        return parsed
    finally:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass


# ─── API publique ───────────────────────────────────────────────────────────


def parse_email_bytes(file_bytes: bytes, filename: str = "") -> ParsedEmail:
    """
    Parse un email à partir de ses bytes.

    Détection du format :
    - Si filename se termine par .msg → format Outlook
    - Sinon → format .eml standard MIME

    Args:
        file_bytes: contenu binaire du fichier email
        filename: nom du fichier (utilisé pour détecter le format)

    Returns:
        ParsedEmail avec métadonnées et pièces jointes extraites.
    """
    if not file_bytes:
        raise ValueError("file_bytes vide")

    fname_lower = (filename or "").lower()
    if fname_lower.endswith(".msg"):
        return _parse_msg(file_bytes)

    # Détection magique : les .msg commencent par D0 CF 11 E0 (signature OLE)
    if file_bytes[:4] == b"\xd0\xcf\x11\xe0":
        return _parse_msg(file_bytes)

    return _parse_eml(file_bytes)


def _guess_mime(filename: str) -> str:
    """Devine le type MIME depuis l'extension du fichier."""
    mime, _ = mimetypes.guess_type(filename)
    if mime:
        return mime
    # Fallback courants
    ext = filename.lower().rsplit(".", 1)[-1] if "." in filename else ""
    fallback = {
        "pdf": "application/pdf",
        "jpg": "image/jpeg",
        "jpeg": "image/jpeg",
        "png": "image/png",
        "tiff": "image/tiff",
        "tif": "image/tiff",
        "webp": "image/webp",
    }
    return fallback.get(ext, "application/octet-stream")


# ─── Helpers d'extraction métier ────────────────────────────────────────────


# Regex VIN — 17 caractères alphanumériques (sans I, O, Q)
VIN_REGEX = re.compile(r"\b([A-HJ-NPR-Z0-9]{17})\b")

# Regex immatriculation française moderne (AA-123-AA)
IMMAT_REGEX = re.compile(r"\b([A-Z]{2}-?\d{3}-?[A-Z]{2})\b")

# Regex téléphone français mobile/fixe
PHONE_REGEX = re.compile(r"(?:\+33|0)\s?[1-9](?:[\s.-]?\d{2}){4}")


def extract_hints_from_email(parsed: ParsedEmail) -> dict:
    """
    Extrait des indices métier du texte de l'email (sujet + corps).

    Ces indices aident le dossier_matcher à proposer un dossier existant
    pour rattacher les nouvelles pièces. Ils sont approximatifs et seront
    confirmés/écrasés par l'OCR des pièces jointes.

    Returns:
        dict avec les clés possibles :
        - vin : str | None
        - immatriculation : str | None
        - sender_email : str
        - phone : str | None
    """
    text = f"{parsed.subject}\n{parsed.body_text}".upper()

    hints: dict = {
        "sender_email": parsed.sender_email,
        "sender_name": parsed.sender_name,
    }

    vin_match = VIN_REGEX.search(text)
    if vin_match:
        hints["vin"] = vin_match.group(1)

    immat_match = IMMAT_REGEX.search(text)
    if immat_match:
        hints["immatriculation"] = immat_match.group(1).replace("-", "").upper()

    phone_match = PHONE_REGEX.search(parsed.body_text)
    if phone_match:
        hints["phone"] = phone_match.group(0).replace(" ", "").replace(".", "").replace("-", "")

    return hints
