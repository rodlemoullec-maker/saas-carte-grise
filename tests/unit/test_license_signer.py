"""
Tests unitaires pour engine.license.signer

Couvre :
- generate_keypair
- sign_license / verify_license (cycle complet)
- sign_payload / verify_payload (signatures arbitraires)
- LicensePayload (is_expired, days_remaining)
- Erreurs : signature invalide, licence expirée, format invalide
"""
from __future__ import annotations

import json
import uuid
from datetime import datetime, timedelta, timezone

import pytest

from engine.license.signer import (
    LicenseExpired,
    LicenseFormatError,
    LicenseInvalidSignature,
    LicensePayload,
    generate_keypair,
    sign_license,
    sign_payload,
    verify_license,
    verify_payload,
)


# ─── Fixtures ───────────────────────────────────────────────────────────────


@pytest.fixture
def keypair() -> tuple[str, str]:
    """Génère une paire Ed25519 fraîche pour chaque test."""
    return generate_keypair()


@pytest.fixture
def valid_payload() -> dict:
    return {
        "license_id": str(uuid.uuid4()),
        "agent_email": "test@cabinet-martin.fr",
        "agent_name": "Cabinet Martin SIV",
        "issued_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "expires_at": (datetime.now(timezone.utc) + timedelta(days=365)).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "type": "annual",
        "version": 1,
    }


# ─── Génération de clés ───────────────────────────────────────────────────


class TestGenerateKeypair:
    def test_returns_two_strings(self) -> None:
        priv, pub = generate_keypair()
        assert isinstance(priv, str)
        assert isinstance(pub, str)

    def test_64_chars_each(self) -> None:
        priv, pub = generate_keypair()
        assert len(priv) == 64
        assert len(pub) == 64

    def test_hex_format(self) -> None:
        priv, pub = generate_keypair()
        # Doivent être convertibles en bytes hex
        bytes.fromhex(priv)
        bytes.fromhex(pub)

    def test_different_each_call(self) -> None:
        p1, _ = generate_keypair()
        p2, _ = generate_keypair()
        assert p1 != p2


# ─── Signature et vérification de licences ───────────────────────────────


class TestSignVerifyCycle:
    def test_sign_then_verify(self, keypair: tuple[str, str], valid_payload: dict) -> None:
        priv, pub = keypair
        token = sign_license(valid_payload, priv)
        verified = verify_license(token, public_key_hex=pub)
        assert verified.agent_email == valid_payload["agent_email"]
        assert verified.type == "annual"

    def test_token_format_payload_dot_signature(self, keypair: tuple[str, str], valid_payload: dict) -> None:
        priv, _ = keypair
        token = sign_license(valid_payload, priv)
        assert "." in token
        parts = token.split(".")
        assert len(parts) == 2
        assert len(parts[0]) > 0
        assert len(parts[1]) > 0

    def test_corrupted_signature_rejected(self, keypair: tuple[str, str], valid_payload: dict) -> None:
        priv, pub = keypair
        token = sign_license(valid_payload, priv)
        # Corrompre la signature (4 derniers caractères)
        bad = token[:-4] + "AAAA"
        with pytest.raises(LicenseInvalidSignature):
            verify_license(bad, public_key_hex=pub)

    def test_wrong_pubkey_rejects(self, valid_payload: dict) -> None:
        priv1, _ = generate_keypair()
        _, pub2 = generate_keypair()  # Autre paire
        token = sign_license(valid_payload, priv1)
        with pytest.raises(LicenseInvalidSignature):
            verify_license(token, public_key_hex=pub2)

    def test_invalid_token_format(self, keypair: tuple[str, str]) -> None:
        _, pub = keypair
        with pytest.raises(LicenseFormatError):
            verify_license("not-a-token", public_key_hex=pub)
        with pytest.raises(LicenseFormatError):
            verify_license("only-one-part", public_key_hex=pub)


# ─── LicensePayload ────────────────────────────────────────────────────────


class TestLicensePayload:
    def test_is_expired_true(self, keypair: tuple[str, str]) -> None:
        priv, pub = keypair
        payload = {
            "license_id": "x",
            "agent_email": "x@x.fr",
            "agent_name": "x",
            "issued_at": "2025-01-01T00:00:00Z",
            "expires_at": "2025-06-01T00:00:00Z",  # Passé
            "type": "annual",
            "version": 1,
        }
        token = sign_license(payload, priv)
        with pytest.raises(LicenseExpired):
            verify_license(token, public_key_hex=pub)

    def test_perpetual_never_expires(self, keypair: tuple[str, str]) -> None:
        priv, pub = keypair
        payload = {
            "license_id": "x",
            "agent_email": "x@x.fr",
            "agent_name": "x",
            "issued_at": "2025-01-01T00:00:00Z",
            "expires_at": "perpetual",
            "type": "perpetual",
            "version": 1,
        }
        token = sign_license(payload, priv)
        verified = verify_license(token, public_key_hex=pub)
        assert verified.is_expired is False
        assert verified.days_remaining is None

    def test_days_remaining_close_to_year(self, keypair: tuple[str, str], valid_payload: dict) -> None:
        priv, pub = keypair
        token = sign_license(valid_payload, priv)
        verified = verify_license(token, public_key_hex=pub)
        # Doit avoir entre 360 et 365 jours
        assert verified.days_remaining is not None
        assert 360 <= verified.days_remaining <= 365

    def test_payload_to_dict(self) -> None:
        p = LicensePayload(
            license_id="abc",
            agent_email="x@x.fr",
            agent_name="X",
            issued_at="2026-01-01T00:00:00Z",
            expires_at="2027-01-01T00:00:00Z",
            type="annual",
            version=1,
        )
        d = p.to_dict()
        assert d["license_id"] == "abc"
        assert d["type"] == "annual"
        assert d["version"] == 1


# ─── sign_payload / verify_payload (signatures arbitraires) ──────────────


class TestSignVerifyPayload:
    def test_sign_arbitrary_bytes(self, keypair: tuple[str, str]) -> None:
        priv, pub = keypair
        data = b"Hello, world!"
        sig = sign_payload(data, priv)
        # Doit pouvoir vérifier sans exception
        verify_payload(data, sig, public_key_hex=pub)

    def test_modified_data_fails(self, keypair: tuple[str, str]) -> None:
        priv, pub = keypair
        data = b"original"
        sig = sign_payload(data, priv)
        with pytest.raises(LicenseInvalidSignature):
            verify_payload(b"modified", sig, public_key_hex=pub)

    def test_sign_json_canonical(self, keypair: tuple[str, str]) -> None:
        """Cas d'usage : signer un bundle JSON canonique."""
        priv, pub = keypair
        data = {"version": "2026.04.01", "rules": {"ocr": {"seuil": 0.5}}}
        canonical = json.dumps(data, separators=(",", ":"), sort_keys=True).encode()
        sig = sign_payload(canonical, priv)
        # Re-sérialisation canonique → même signature valide
        canonical2 = json.dumps(data, separators=(",", ":"), sort_keys=True).encode()
        verify_payload(canonical2, sig, public_key_hex=pub)
