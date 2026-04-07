"""
Tests unitaires pour engine.rules.loader

Couvre :
- Chargement du bundle par défaut
- get_rule avec clés pointées
- Fallback sur clé inexistante
- save_local_bundle + reload (cycle complet)
- RulesBundle.get
- Bundle local signé prime sur le bundle par défaut
"""
from __future__ import annotations

import json
import os
import shutil
import tempfile

import pytest

import engine.license.signer as signer_module
from engine.license.signer import generate_keypair, sign_payload
from engine.rules.default_bundle import DEFAULT_BUNDLE_VERSION, get_default_bundle
from engine.rules.loader import RulesBundle


# ─── Fixtures ───────────────────────────────────────────────────────────────


@pytest.fixture
def tmp_storage(monkeypatch):
    """
    Crée un dossier temporaire et patche STORAGE_PATH pour qu'il pointe dedans.
    Réinitialise le singleton du loader entre chaque test.
    """
    d = tempfile.mkdtemp(prefix="imatra_rules_test_")
    monkeypatch.setenv("STORAGE_PATH", os.path.join(d, "documents"))

    # Reset les caches
    from config.settings import get_settings
    get_settings.cache_clear()

    import engine.rules.loader as loader_module
    loader_module._current_bundle = None

    yield d

    shutil.rmtree(d, ignore_errors=True)
    loader_module._current_bundle = None
    get_settings.cache_clear()


@pytest.fixture
def keypair_patched():
    """Génère et patche la clé publique embarquée."""
    priv, pub = generate_keypair()
    original = signer_module.PUBLIC_KEY_HEX
    signer_module.PUBLIC_KEY_HEX = pub
    yield priv, pub
    signer_module.PUBLIC_KEY_HEX = original


# ─── RulesBundle dataclass ─────────────────────────────────────────────────


class TestRulesBundle:
    def test_get_simple_key(self) -> None:
        b = RulesBundle(
            version="2026.04.01",
            description="test",
            released_at="2026-04-01",
            source="default",
            data={"ocr": {"seuil": 0.5}},
        )
        assert b.get("ocr.seuil") == 0.5

    def test_get_nested_key(self) -> None:
        b = RulesBundle(
            version="x", description="x", released_at="x", source="default",
            data={"taxes": {"y1_par_departement": {"75": 46.15}}},
        )
        assert b.get("taxes.y1_par_departement.75") == 46.15

    def test_get_missing_returns_default(self) -> None:
        b = RulesBundle(
            version="x", description="x", released_at="x", source="default",
            data={"a": {"b": 1}},
        )
        assert b.get("a.b.c", default=999) == 999
        assert b.get("zzz", default="fallback") == "fallback"

    def test_to_dict(self) -> None:
        b = RulesBundle(
            version="v1", description="d", released_at="r",
            source="default", data={"k": "v"},
        )
        d = b.to_dict()
        assert d["version"] == "v1"
        assert d["source"] == "default"
        assert d["data"] == {"k": "v"}


# ─── default_bundle ────────────────────────────────────────────────────────


class TestDefaultBundle:
    def test_default_bundle_has_version(self) -> None:
        bundle = get_default_bundle()
        assert "version" in bundle
        assert bundle["version"] == DEFAULT_BUNDLE_VERSION

    def test_default_bundle_has_ocr_section(self) -> None:
        bundle = get_default_bundle()
        assert "ocr" in bundle
        assert "seuil_illisible" in bundle["ocr"]

    def test_default_bundle_has_taxes(self) -> None:
        bundle = get_default_bundle()
        assert "taxes" in bundle
        assert "y1_par_departement" in bundle["taxes"]
        assert "75" in bundle["taxes"]["y1_par_departement"]

    def test_default_bundle_returns_copy(self) -> None:
        """Modifier le bundle ne doit pas affecter les appels suivants."""
        b1 = get_default_bundle()
        b1["ocr"]["seuil_illisible"] = 999
        b2 = get_default_bundle()
        assert b2["ocr"]["seuil_illisible"] != 999


# ─── Loader ────────────────────────────────────────────────────────────────


class TestLoader:
    def test_loads_default_when_no_local(self, tmp_storage) -> None:
        from engine.rules.loader import get_current_bundle
        bundle = get_current_bundle()
        assert bundle.source == "default"
        assert bundle.version == DEFAULT_BUNDLE_VERSION

    def test_get_rule_from_default(self, tmp_storage) -> None:
        from engine.rules import get_rule
        # Doit charger le bundle par défaut et retourner les valeurs
        seuil = get_rule("ocr.seuil_illisible")
        assert seuil == 0.40

    def test_get_rule_with_fallback(self, tmp_storage) -> None:
        from engine.rules import get_rule
        # Clé inexistante → fallback
        val = get_rule("does.not.exist", default=42)
        assert val == 42

    def test_get_rule_paris_tarif(self, tmp_storage) -> None:
        from engine.rules import get_rule
        tarif = get_rule("taxes.y1_par_departement.75")
        assert tarif == 46.15


# ─── save_local_bundle + reload ───────────────────────────────────────────


class TestSaveAndReload:
    def test_save_and_reload_signed_bundle(self, tmp_storage, keypair_patched) -> None:
        priv, _ = keypair_patched
        from engine.rules.loader import save_local_bundle, reload as reload_bundle, get_current_bundle

        new_bundle = {
            "version": "2027.01.01",
            "description": "Test bundle 2027",
            "released_at": "2027-01-01T00:00:00Z",
            "ocr": {
                "seuil_illisible": 0.55,
                "seuil_avertissement": 0.80,
            },
        }

        canonical = json.dumps(new_bundle, separators=(",", ":"), sort_keys=True).encode()
        sig = sign_payload(canonical, priv)
        save_local_bundle(new_bundle, sig)

        # Recharger
        loaded = reload_bundle()
        assert loaded.source == "local_signed"
        assert loaded.version == "2027.01.01"
        assert loaded.get("ocr.seuil_illisible") == 0.55

    def test_corrupted_signature_falls_back_to_default(self, tmp_storage, keypair_patched) -> None:
        priv, _ = keypair_patched
        from engine.rules.loader import save_local_bundle, reload as reload_bundle

        new_bundle = {"version": "2027.01.01", "ocr": {"seuil_illisible": 0.99}}
        canonical = json.dumps(new_bundle, separators=(",", ":"), sort_keys=True).encode()
        sig = sign_payload(canonical, priv)

        # Sauver normalement
        save_local_bundle(new_bundle, sig[:-4] + "XXXX")  # Signature corrompue

        # Le reload doit détecter la signature invalide et tomber en fallback
        loaded = reload_bundle()
        assert loaded.source == "default"
        assert loaded.version == DEFAULT_BUNDLE_VERSION
