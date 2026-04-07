"""Tests pour le module SMS."""
from notifications.sms import build_sms_client_link, build_sms_otp


def test_build_sms_client_link_vendeur():
    """Le SMS vendeur doit contenir le lien et le nom du commerce."""
    msg = build_sms_client_link(
        client_prenom="Marie",
        nom_commerce="Dupont Motos",
        lien="https://app.autodocpro.fr/client/abc123",
        telephone_commerce="01 23 45 67 89",
        type_compte="VENDEUR_HABILITE",
    )
    assert "Marie" in msg
    assert "Dupont Motos" in msg
    assert "https://app.autodocpro.fr/client/abc123" in msg
    assert "01 23 45 67 89" in msg
    assert "AutoDoc Pro" in msg


def test_build_sms_client_link_agent():
    """Le SMS agent doit avoir un intro different."""
    msg = build_sms_client_link(
        client_prenom=None,
        nom_commerce="Garage Central",
        lien="https://example.com",
        telephone_commerce="06 00 00 00 00",
        type_compte="AGENT_HABILITE",
    )
    assert "traite votre demande" in msg
    assert "AutoDoc Pro" not in msg.split("traite")[0]  # pas dans l'intro agent


def test_build_sms_otp():
    """Le SMS OTP doit contenir le code."""
    msg = build_sms_otp("123456")
    assert "123456" in msg
    assert "10 minutes" in msg


def test_sms_length():
    """Le SMS ne doit pas depasser ~320 chars (2 SMS)."""
    msg = build_sms_client_link(
        client_prenom="Jean-Pierre",
        nom_commerce="Automobiles du Centre",
        lien="https://app.autodocpro.fr/client/abcdefghijk",
        telephone_commerce="01 23 45 67 89",
    )
    assert len(msg) < 320
