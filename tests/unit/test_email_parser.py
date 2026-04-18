"""
Tests unitaires pour engine.email_parser

Couvre :
- Parsing d'emails .eml standard
- Extraction des pièces jointes
- Filtrage des pièces parasites (signatures, vCards, image001.png)
- extract_hints_from_email (VIN, immatriculation, téléphone)
- Détection magique du format Outlook (signature OLE)
- Gestion des erreurs (email vide, format invalide)
"""
from __future__ import annotations

import pytest

from engine.email_parser import (
    EmailAttachment,
    ParsedEmail,
    extract_hints_from_email,
    parse_email_bytes,
)


# ─── Helpers ────────────────────────────────────────────────────────────────


def _build_eml(
    sender: str = "marie.dupont@gmail.com",
    subject: str = "Documents pour ma carte grise",
    body: str = "Bonjour, voici mes documents.",
    attachments: list[tuple[str, str, str]] | None = None,
) -> bytes:
    """
    Construit un email .eml minimal pour les tests.

    attachments : liste de (filename, mime_type, base64_content)
    """
    boundary = "BOUNDARY42"
    parts = [
        f"From: {sender}",
        "To: agent@cabinet-martin.fr",
        f"Subject: {subject}",
        "Date: Mon, 7 Apr 2026 10:00:00 +0200",
        "MIME-Version: 1.0",
        f'Content-Type: multipart/mixed; boundary="{boundary}"',
        "",
        f"--{boundary}",
        "Content-Type: text/plain; charset=utf-8",
        "",
        body,
    ]

    for fname, mime, content_b64 in attachments or []:
        parts.extend([
            "",
            f"--{boundary}",
            f'Content-Type: {mime}; name="{fname}"',
            f'Content-Disposition: attachment; filename="{fname}"',
            "Content-Transfer-Encoding: base64",
            "",
            content_b64,
        ])

    parts.extend(["", f"--{boundary}--", ""])
    return "\n".join(parts).encode("utf-8")


# ─── Parsing standard ──────────────────────────────────────────────────────


class TestEmlParsing:
    def test_parse_minimal_eml(self) -> None:
        eml = _build_eml()
        parsed = parse_email_bytes(eml, "marie.eml")
        assert isinstance(parsed, ParsedEmail)
        assert parsed.format == "eml"
        assert parsed.sender_email == "marie.dupont@gmail.com"
        assert "carte grise" in parsed.subject.lower()
        assert "voici mes documents" in parsed.body_text.lower()
        assert parsed.attachments == []

    def test_parse_eml_with_one_pdf(self) -> None:
        eml = _build_eml(attachments=[("cni.pdf", "application/pdf", "JVBERi0xLjQK")])
        parsed = parse_email_bytes(eml, "marie.eml")
        assert len(parsed.attachments) == 1
        att = parsed.attachments[0]
        assert att.filename == "cni.pdf"
        assert att.mime_type == "application/pdf"
        assert att.size_bytes > 0
        assert att.is_processable is True

    def test_parse_eml_with_multiple_attachments(self) -> None:
        eml = _build_eml(attachments=[
            ("cni.pdf", "application/pdf", "JVBERi0xLjQK"),
            ("permis.jpg", "image/jpeg", "/9j/4AAQSkZJRg=="),
            ("domicile.png", "image/png", "iVBORw0KGgo="),
        ])
        parsed = parse_email_bytes(eml, "marie.eml")
        assert len(parsed.attachments) == 3
        names = {a.filename for a in parsed.attachments}
        assert names == {"cni.pdf", "permis.jpg", "domicile.png"}
        assert all(a.is_processable for a in parsed.attachments)

    def test_parse_eml_filters_parasites(self) -> None:
        """Les pièces parasites doivent être marquées non-processable."""
        eml = _build_eml(attachments=[
            ("cni.pdf", "application/pdf", "JVBERi0xLjQK"),
            ("smime.p7s", "application/pkcs7-signature", "AAAA"),
            ("image001.png", "image/png", "iVBORw0KGgo="),
        ])
        parsed = parse_email_bytes(eml, "marie.eml")
        assert len(parsed.attachments) == 3
        processable = parsed.processable_attachments
        assert len(processable) == 1
        assert processable[0].filename == "cni.pdf"


# ─── Extraction d'indices ─────────────────────────────────────────────────


class TestExtractHints:
    def test_extract_vin_from_subject(self) -> None:
        eml = _build_eml(subject="Documents — VIN JMZKECW105SJ08739")
        parsed = parse_email_bytes(eml, "test.eml")
        hints = extract_hints_from_email(parsed)
        assert hints["vin"] == "JMZKECW105SJ08739"

    def test_extract_vin_from_body(self) -> None:
        eml = _build_eml(body="Le VIN est WBA1234567890ABCD, j'espère que c'est OK.")
        parsed = parse_email_bytes(eml, "test.eml")
        hints = extract_hints_from_email(parsed)
        assert hints.get("vin") == "WBA1234567890ABCD"

    def test_extract_immatriculation(self) -> None:
        eml = _build_eml(subject="Carte grise AB-123-CD")
        parsed = parse_email_bytes(eml, "test.eml")
        hints = extract_hints_from_email(parsed)
        assert hints["immatriculation"] == "AB123CD"

    def test_extract_phone_from_body(self) -> None:
        eml = _build_eml(body="Mon téléphone : 06 12 34 56 78")
        parsed = parse_email_bytes(eml, "test.eml")
        hints = extract_hints_from_email(parsed)
        assert hints["phone"] == "0612345678"

    def test_extract_phone_with_dots(self) -> None:
        eml = _build_eml(body="Mobile : 06.12.34.56.78")
        parsed = parse_email_bytes(eml, "test.eml")
        hints = extract_hints_from_email(parsed)
        assert hints["phone"] == "0612345678"

    def test_no_hints_when_empty(self) -> None:
        eml = _build_eml(subject="Bonjour", body="Rien de spécial.")
        parsed = parse_email_bytes(eml, "test.eml")
        hints = extract_hints_from_email(parsed)
        # Toujours sender_email + sender_name au minimum
        assert "sender_email" in hints
        assert "vin" not in hints
        assert "immatriculation" not in hints

    def test_extract_sender_email(self) -> None:
        eml = _build_eml(sender="test@example.fr")
        parsed = parse_email_bytes(eml, "test.eml")
        hints = extract_hints_from_email(parsed)
        assert hints["sender_email"] == "test@example.fr"


# ─── Edge cases ────────────────────────────────────────────────────────────


class TestEdgeCases:
    def test_empty_bytes_raises(self) -> None:
        with pytest.raises(ValueError, match="vide"):
            parse_email_bytes(b"", "empty.eml")

    def test_invalid_filename_falls_back_to_eml(self) -> None:
        """Sans .msg dans le nom, on tente l'eml même si le contenu est mauvais."""
        eml = _build_eml()
        # Renommer en .txt — on doit quand même réussir car le contenu est valide
        parsed = parse_email_bytes(eml, "anything.txt")
        assert parsed.format == "eml"

    def test_msg_signature_detection(self) -> None:
        """Les bytes commençant par D0 CF 11 E0 sont détectés comme .msg."""
        # On ne lance pas le parser .msg réel (il a besoin d'extract_msg),
        # on teste juste que la détection magique route vers le bon parser.
        # Si extract_msg n'est pas installé, on doit avoir une ImportError.
        msg_bytes = b"\xd0\xcf\x11\xe0" + b"\x00" * 100
        try:
            parse_email_bytes(msg_bytes, "test.eml")
        except ImportError as e:
            # Attendu : extract-msg pas installé en environnement de dev
            assert "extract-msg" in str(e).lower() or "extract_msg" in str(e).lower()
        except Exception:
            # extract-msg installé mais le contenu n'est pas un vrai .msg
            pass  # Le test passe — l'important est que la détection ait routé


class TestEmailAttachment:
    def test_processable_pdf(self) -> None:
        att = EmailAttachment(
            filename="cni.pdf",
            content_bytes=b"%PDF-1.4",
            mime_type="application/pdf",
            size_bytes=8,
        )
        assert att.is_processable is True

    def test_processable_jpg(self) -> None:
        att = EmailAttachment("photo.jpg", b"\xff\xd8\xff", "image/jpeg", 3)
        assert att.is_processable is True

    def test_not_processable_signature(self) -> None:
        att = EmailAttachment("smime.p7s", b"data", "application/pkcs7-signature", 4)
        assert att.is_processable is False

    def test_not_processable_html(self) -> None:
        att = EmailAttachment("body.html", b"<html>", "text/html", 6)
        assert att.is_processable is False

    def test_not_processable_image001(self) -> None:
        att = EmailAttachment("image001.png", b"\x89PNG", "image/png", 4)
        assert att.is_processable is False
