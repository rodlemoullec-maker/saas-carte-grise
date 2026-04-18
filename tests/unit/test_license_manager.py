"""
Tests unitaires pour engine.license.manager

Couvre :
- Mode essai (démarrage, jours restants, dossiers consommés)
- Mode essai épuisé (par jours OU par dossiers)
- Activation d'une licence valide
- Désactivation
- Persistance entre instances
"""
from __future__ import annotations

import shutil
import tempfile
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

import engine.license.signer as signer_module
from engine.license.manager import (
    TRIAL_DURATION_DAYS,
    TRIAL_MAX_DOSSIERS,
    LicenseManager,
)
from engine.license.signer import generate_keypair, sign_license


# ─── Fixtures ───────────────────────────────────────────────────────────────


@pytest.fixture
def tmp_dir():
    """Dossier temporaire isolé pour chaque test."""
    d = tempfile.mkdtemp(prefix="imatra_lic_test_")
    yield d
    shutil.rmtree(d, ignore_errors=True)


@pytest.fixture
def keypair_patched():
    """Génère une paire et patche PUBLIC_KEY_HEX pour la durée du test."""
    priv, pub = generate_keypair()
    original = signer_module.PUBLIC_KEY_HEX
    signer_module.PUBLIC_KEY_HEX = pub
    yield priv, pub
    signer_module.PUBLIC_KEY_HEX = original


def _make_token(priv: str, days: int = 365, type_: str = "annual") -> str:
    payload = {
        "license_id": str(uuid.uuid4()),
        "agent_email": "test@imatra.fr",
        "agent_name": "Test Agent",
        "issued_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "expires_at": (datetime.now(timezone.utc) + timedelta(days=days)).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "type": type_,
        "version": 1,
    }
    return sign_license(payload, priv)


# ─── Mode essai ─────────────────────────────────────────────────────────────


class TestTrialMode:
    def test_first_launch_starts_trial(self, tmp_dir: str) -> None:
        mgr = LicenseManager(base_path=tmp_dir)
        status = mgr.get_status(dossiers_used_count=0)
        assert status.mode == "trial"
        assert status.is_valid is True
        assert status.trial_days_remaining == TRIAL_DURATION_DAYS

    def test_trial_started_at_persisted(self, tmp_dir: str) -> None:
        mgr1 = LicenseManager(base_path=tmp_dir)
        s1 = mgr1.get_status(dossiers_used_count=0)
        # Nouvelle instance → doit lire le marqueur existant
        mgr2 = LicenseManager(base_path=tmp_dir)
        s2 = mgr2.get_status(dossiers_used_count=0)
        assert s1.trial_started_at == s2.trial_started_at

    def test_dossiers_used_decreases_remaining(self, tmp_dir: str) -> None:
        mgr = LicenseManager(base_path=tmp_dir)
        # 5 dossiers consommés sur 10
        status = mgr.get_status(dossiers_used_count=5)
        assert status.is_valid is True
        # Le message doit refléter "5 dossiers restants"
        assert "5 dossier" in status.message

    def test_trial_exhausted_by_dossiers(self, tmp_dir: str) -> None:
        mgr = LicenseManager(base_path=tmp_dir)
        status = mgr.get_status(dossiers_used_count=TRIAL_MAX_DOSSIERS + 5)
        assert status.is_valid is False
        assert status.mode == "expired"
        assert "terminée" in status.message.lower()


# ─── Activation de licence ─────────────────────────────────────────────────


class TestActivation:
    def test_activate_valid_token(self, tmp_dir: str, keypair_patched) -> None:
        priv, _ = keypair_patched
        mgr = LicenseManager(base_path=tmp_dir)
        token = _make_token(priv, days=365)
        payload = mgr.activate(token)
        assert payload.agent_email == "test@imatra.fr"
        assert payload.type == "annual"

    def test_status_after_activation(self, tmp_dir: str, keypair_patched) -> None:
        priv, _ = keypair_patched
        mgr = LicenseManager(base_path=tmp_dir)
        mgr.activate(_make_token(priv, days=180))
        status = mgr.get_status(dossiers_used_count=999)  # ignoré en mode licensed
        assert status.mode == "licensed"
        assert status.is_valid is True
        assert status.payload is not None
        assert status.payload.agent_email == "test@imatra.fr"

    def test_activated_license_persists(self, tmp_dir: str, keypair_patched) -> None:
        priv, _ = keypair_patched
        mgr1 = LicenseManager(base_path=tmp_dir)
        mgr1.activate(_make_token(priv, days=365))

        # Nouvelle instance → la licence doit toujours être active
        mgr2 = LicenseManager(base_path=tmp_dir)
        status = mgr2.get_status()
        assert status.mode == "licensed"

    def test_deactivate_returns_to_trial(self, tmp_dir: str, keypair_patched) -> None:
        priv, _ = keypair_patched
        mgr = LicenseManager(base_path=tmp_dir)
        mgr.activate(_make_token(priv))
        assert mgr.get_status().mode == "licensed"

        mgr.deactivate()
        status = mgr.get_status(dossiers_used_count=0)
        assert status.mode == "trial"

    def test_perpetual_license(self, tmp_dir: str, keypair_patched) -> None:
        priv, _ = keypair_patched
        # Construire un token perpetual à la main
        payload = {
            "license_id": str(uuid.uuid4()),
            "agent_email": "perp@imatra.fr",
            "agent_name": "Perpetual Agent",
            "issued_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "expires_at": "perpetual",
            "type": "perpetual",
            "version": 1,
        }
        token = sign_license(payload, priv)
        mgr = LicenseManager(base_path=tmp_dir)
        mgr.activate(token)
        status = mgr.get_status()
        assert status.mode == "licensed"
        assert status.payload is not None
        assert status.payload.type == "perpetual"
