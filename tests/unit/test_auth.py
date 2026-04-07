"""Tests pour le module d'authentification JWT."""
from api.auth import _create_access_token, _verify_token, hash_password, verify_password
from uuid import uuid4
import os

# S'assurer qu'un secret est defini pour les tests
os.environ.setdefault("APP_SECRET_KEY", "test-secret-key-for-unit-tests")


def test_create_and_verify_token():
    """Un token cree doit etre verifiable et contenir le bon sub."""
    pro_id = uuid4()
    token, expires_in = _create_access_token(pro_id, "test@example.com")

    assert isinstance(token, str)
    assert len(token) > 20
    assert expires_in > 0

    payload = _verify_token(token)
    assert payload["sub"] == str(pro_id)
    assert payload["email"] == "test@example.com"
    assert "exp" in payload


def test_invalid_token_raises():
    """Un token invalide doit lever une HTTPException."""
    from fastapi import HTTPException
    import pytest

    with pytest.raises(HTTPException) as exc_info:
        _verify_token("invalid.token.here")
    assert exc_info.value.status_code == 401


def test_password_hash():
    """Le hash bcrypt doit etre verifiable."""
    password = "monMotDePasse123!"
    hashed = hash_password(password)

    assert hashed != password
    assert verify_password(password, hashed)
    assert not verify_password("mauvais", hashed)


def test_token_contains_expiry():
    """Le token doit avoir une date d'expiration."""
    pro_id = uuid4()
    token, _ = _create_access_token(pro_id, "test@test.fr")
    payload = _verify_token(token)
    assert payload["exp"] > 0
