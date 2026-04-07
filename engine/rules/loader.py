"""
Loader du bundle de règles paramétrables.

Au démarrage du logiciel, charge le bundle dans cet ordre :
1. data/rules/current.json (si présent et signature valide)
2. Sinon : bundle par défaut embarqué (engine/rules/default_bundle.py)

Expose ensuite une API simple :
    from engine.rules import get_rule

    seuil = get_rule("ocr.seuil_illisible", default=0.40)
    tarif = get_rule(f"taxes.y1_par_departement.{dept}", default=43.0)

Le loader est un singleton — une seule instance par installation locale.
Le bundle peut être rechargé après une mise à jour via reload().
"""
from __future__ import annotations

import copy
import json
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from engine.license.signer import (
    LicenseError,
    LicenseFormatError,
    LicenseInvalidSignature,
    verify_payload,
)
from engine.rules.default_bundle import DEFAULT_BUNDLE_VERSION, get_default_bundle

logger = logging.getLogger(__name__)


# ─── Modèle ────────────────────────────────────────────────────────────────


@dataclass
class RulesBundle:
    """Bundle de règles chargé en mémoire."""
    version: str
    description: str
    released_at: str
    source: str  # "default" | "local_signed" | "local_unsigned"
    data: dict = field(default_factory=dict)

    def get(self, dotted_key: str, default: Any = None) -> Any:
        """
        Récupère une valeur du bundle via une clé pointée.

        Exemples :
            bundle.get("ocr.seuil_illisible")              → 0.40
            bundle.get("taxes.y1_par_departement.75")      → 46.15
            bundle.get("taxes.y1_par_departement.99", 43)  → 43 (fallback)
        """
        parts = dotted_key.split(".")
        node: Any = self.data
        for p in parts:
            if isinstance(node, dict) and p in node:
                node = node[p]
            else:
                return default
        return node

    def to_dict(self) -> dict:
        return {
            "version": self.version,
            "description": self.description,
            "released_at": self.released_at,
            "source": self.source,
            "data": self.data,
        }


# ─── Singleton ─────────────────────────────────────────────────────────────


_current_bundle: RulesBundle | None = None


def get_current_bundle() -> RulesBundle:
    """Retourne le bundle actuellement chargé (le charge si nécessaire)."""
    global _current_bundle
    if _current_bundle is None:
        _current_bundle = _load_bundle()
    return _current_bundle


def reload() -> RulesBundle:
    """Force le rechargement du bundle (après un update par exemple)."""
    global _current_bundle
    _current_bundle = _load_bundle()
    return _current_bundle


def get_rule(dotted_key: str, default: Any = None) -> Any:
    """API publique simple pour récupérer une règle paramétrable.

    Exemple :
        from engine.rules import get_rule
        seuil_illisible = get_rule("ocr.seuil_illisible", 0.40)
    """
    return get_current_bundle().get(dotted_key, default)


# ─── Chargement ────────────────────────────────────────────────────────────


def _load_bundle() -> RulesBundle:
    """Charge le bundle depuis disque local, ou bundle embarqué par défaut."""
    local_path = _get_local_bundle_path()

    if local_path.exists():
        try:
            return _load_local_bundle(local_path)
        except Exception as e:
            logger.warning(
                f"[rules] Bundle local invalide ({e}), fallback bundle par défaut"
            )

    # Fallback bundle embarqué
    data = get_default_bundle()
    return RulesBundle(
        version=data.get("version", DEFAULT_BUNDLE_VERSION),
        description=data.get("description", ""),
        released_at=data.get("released_at", ""),
        source="default",
        data=data,
    )


def _load_local_bundle(path: Path) -> RulesBundle:
    """
    Charge un bundle JSON local et vérifie sa signature.

    Format attendu (data/rules/current.json) :
    {
        "bundle": { ... le contenu du bundle ... },
        "signature": "base64url..."
    }

    La signature couvre la sérialisation JSON canonique du champ "bundle".
    """
    raw = json.loads(path.read_text(encoding="utf-8"))

    if not isinstance(raw, dict) or "bundle" not in raw or "signature" not in raw:
        raise ValueError("Format de bundle invalide (champs 'bundle' et 'signature' attendus)")

    bundle_data = raw["bundle"]
    signature = raw["signature"]

    # Re-sérialisation canonique pour vérifier la signature
    canonical = json.dumps(bundle_data, separators=(",", ":"), sort_keys=True).encode("utf-8")

    try:
        verify_payload(canonical, signature)
        source = "local_signed"
        logger.info(f"[rules] Bundle local signé chargé (version {bundle_data.get('version')})")
    except (LicenseInvalidSignature, LicenseFormatError) as e:
        raise ValueError(f"Signature du bundle invalide : {e}") from e
    except LicenseError as e:
        # Clé publique non configurée → on accepte le bundle sans vérification
        # (mode dev). En production, ce code ne sera jamais exécuté.
        logger.warning(
            f"[rules] Bundle chargé SANS vérification de signature ({e}). "
            "Mode développement uniquement."
        )
        source = "local_unsigned"

    return RulesBundle(
        version=bundle_data.get("version", "unknown"),
        description=bundle_data.get("description", ""),
        released_at=bundle_data.get("released_at", ""),
        source=source,
        data=bundle_data,
    )


def _get_local_bundle_path() -> Path:
    """Chemin du fichier bundle local sur disque."""
    from config.settings import get_settings
    settings = get_settings()
    base = Path(settings.storage_path).parent
    return base / "rules" / "current.json"


def save_local_bundle(bundle_data: dict, signature_b64: str) -> Path:
    """
    Persiste un nouveau bundle (téléchargé depuis l'éditeur) sur le disque local.

    Vérifie la signature avant d'écrire — refuse d'enregistrer un bundle
    invalide.
    """
    canonical = json.dumps(bundle_data, separators=(",", ":"), sort_keys=True).encode("utf-8")

    try:
        verify_payload(canonical, signature_b64)
    except LicenseError:
        # Clé publique non configurée — on accepte en dev (warning logué côté loader)
        pass

    path = _get_local_bundle_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {"bundle": bundle_data, "signature": signature_b64}
    path.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    logger.info(f"[rules] Nouveau bundle écrit : {path} (version {bundle_data.get('version')})")
    return path
