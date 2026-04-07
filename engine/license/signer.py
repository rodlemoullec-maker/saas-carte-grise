"""
Signature et vérification de licences avec Ed25519.

Format d'une licence (token signé) :

    base64url(payload_json) + "." + base64url(signature)

Le payload est un dict JSON :

    {
        "license_id": "uuid-string",
        "agent_email": "agent@example.com",
        "agent_name": "Cabinet Martin SIV",
        "issued_at": "2026-04-07T10:00:00Z",
        "expires_at": "2027-04-07T10:00:00Z",
        "type": "annual" | "perpetual" | "trial",
        "version": 1
    }

Vérification :
- Décoder le payload + la signature
- Vérifier la signature Ed25519 avec la clé publique embarquée
- Vérifier que la licence n'est pas expirée
- Vérifier que le type est valide

Génération (côté éditeur uniquement, via scripts/generate_license.py) :
- Construire le payload
- Signer avec la clé privée
- Encoder en base64url

La clé publique est embarquée dans le code source de chaque installation
(constante PUBLIC_KEY_HEX). La clé privée reste chez l'éditeur.
"""
from __future__ import annotations

import base64
import json
import logging
from dataclasses import dataclass
from datetime import datetime, timezone

logger = logging.getLogger(__name__)


# ─── Clé publique de l'éditeur ─────────────────────────────────────────────
#
# Cette clé est embarquée dans le binaire/code source de chaque installation.
# Elle permet de vérifier les licences signées par l'éditeur.
#
# La clé privée correspondante reste chez l'éditeur. Elle ne doit JAMAIS être
# diffusée. Compromission = toutes les licences peuvent être falsifiées.
#
# Pour le développement, on utilise une clé "dev" générée localement.
# En production, l'éditeur génère sa propre paire et remplace cette constante.
#
# Format : 64 caractères hexadécimaux (32 bytes raw)
#
# Pour générer une nouvelle paire (dev) :
#     python scripts/generate_license_keypair.py
# ────────────────────────────────────────────────────────────────────────────

PUBLIC_KEY_HEX = (
    "0000000000000000000000000000000000000000000000000000000000000000"
)


# ─── Erreurs ───────────────────────────────────────────────────────────────


class LicenseError(Exception):
    """Erreur générique de licence."""


class LicenseInvalidSignature(LicenseError):
    """La signature ne correspond pas au payload."""


class LicenseExpired(LicenseError):
    """La licence est expirée."""


class LicenseFormatError(LicenseError):
    """Format de licence invalide (token mal formé, base64 cassée, JSON cassé)."""


class LicenseTypeUnknown(LicenseError):
    """Type de licence non reconnu."""


# ─── Modèle de données ────────────────────────────────────────────────────


@dataclass
class LicensePayload:
    """Contenu déchiffré d'une licence."""
    license_id: str
    agent_email: str
    agent_name: str
    issued_at: str  # ISO 8601 UTC
    expires_at: str  # ISO 8601 UTC ou "perpetual"
    type: str  # "annual" | "perpetual" | "trial"
    version: int = 1

    @property
    def is_expired(self) -> bool:
        if self.type == "perpetual" or self.expires_at == "perpetual":
            return False
        try:
            exp = _parse_iso(self.expires_at)
            return datetime.now(timezone.utc) > exp
        except Exception:
            return True

    @property
    def days_remaining(self) -> int | None:
        """Jours restants avant expiration. None si perpétuelle."""
        if self.type == "perpetual" or self.expires_at == "perpetual":
            return None
        try:
            exp = _parse_iso(self.expires_at)
            delta = exp - datetime.now(timezone.utc)
            return max(0, delta.days)
        except Exception:
            return 0

    def to_dict(self) -> dict:
        return {
            "license_id": self.license_id,
            "agent_email": self.agent_email,
            "agent_name": self.agent_name,
            "issued_at": self.issued_at,
            "expires_at": self.expires_at,
            "type": self.type,
            "version": self.version,
        }


# ─── Vérification (utilisée côté agent local) ──────────────────────────────


def verify_license(token: str, public_key_hex: str | None = None) -> LicensePayload:
    """
    Vérifie une licence et retourne son contenu.

    Args:
        token: la chaîne "payload_b64.signature_b64"
        public_key_hex: clé publique en hex (par défaut PUBLIC_KEY_HEX)

    Raises:
        LicenseFormatError: si le token est mal formé
        LicenseInvalidSignature: si la signature est invalide
        LicenseExpired: si la licence est expirée
        LicenseTypeUnknown: si le type n'est pas reconnu

    Returns:
        LicensePayload avec le contenu vérifié
    """
    pub_hex = (public_key_hex or PUBLIC_KEY_HEX).strip()
    if not pub_hex or pub_hex == "00" * 32:
        raise LicenseError(
            "Clé publique d'éditeur non configurée. "
            "Lancez `python scripts/generate_license_keypair.py` pour générer "
            "une paire de clés de développement."
        )

    # Parse "payload.signature"
    if "." not in token:
        raise LicenseFormatError("Format de licence invalide (séparateur '.' manquant)")
    parts = token.strip().split(".", 1)
    if len(parts) != 2:
        raise LicenseFormatError("Format de licence invalide")

    try:
        payload_bytes = _b64url_decode(parts[0])
        signature_bytes = _b64url_decode(parts[1])
    except Exception as e:
        raise LicenseFormatError(f"Encodage base64 invalide : {e}") from e

    # Vérifier la signature
    try:
        from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
        public_key = Ed25519PublicKey.from_public_bytes(bytes.fromhex(pub_hex))
        public_key.verify(signature_bytes, payload_bytes)
    except ImportError as e:
        raise LicenseError(
            "Le package `cryptography` est requis pour vérifier les licences. "
            "Installez avec : pip install cryptography"
        ) from e
    except Exception as e:
        raise LicenseInvalidSignature(f"Signature invalide : {e}") from e

    # Décoder le payload
    try:
        payload_dict = json.loads(payload_bytes.decode("utf-8"))
    except Exception as e:
        raise LicenseFormatError(f"Payload JSON invalide : {e}") from e

    # Construire le LicensePayload
    try:
        payload = LicensePayload(
            license_id=payload_dict["license_id"],
            agent_email=payload_dict["agent_email"],
            agent_name=payload_dict.get("agent_name", ""),
            issued_at=payload_dict["issued_at"],
            expires_at=payload_dict["expires_at"],
            type=payload_dict["type"],
            version=payload_dict.get("version", 1),
        )
    except KeyError as e:
        raise LicenseFormatError(f"Champ manquant dans la licence : {e}") from e

    if payload.type not in ("annual", "perpetual", "trial"):
        raise LicenseTypeUnknown(f"Type de licence inconnu : {payload.type}")

    if payload.is_expired:
        raise LicenseExpired(
            f"Licence expirée le {payload.expires_at}. "
            f"Renouvelez votre licence pour continuer à utiliser AutoDoc Pro."
        )

    return payload


# ─── Génération (utilisée côté éditeur uniquement) ─────────────────────────


def sign_license(payload: dict, private_key_hex: str) -> str:
    """
    Signe un payload de licence avec la clé privée Ed25519.

    Cette fonction est utilisée par scripts/generate_license.py et ne doit
    pas être appelée depuis le code de l'agent (qui n'a pas la clé privée).

    Args:
        payload: dict respectant le schéma LicensePayload
        private_key_hex: clé privée Ed25519 en hex (64 caractères)

    Returns:
        token "payload_b64.signature_b64"
    """
    try:
        from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
    except ImportError as e:
        raise LicenseError("Le package `cryptography` est requis") from e

    payload_json = json.dumps(payload, separators=(",", ":"), sort_keys=True)
    payload_bytes = payload_json.encode("utf-8")

    private_key = Ed25519PrivateKey.from_private_bytes(bytes.fromhex(private_key_hex))
    signature = private_key.sign(payload_bytes)

    return f"{_b64url_encode(payload_bytes)}.{_b64url_encode(signature)}"


def sign_payload(payload_bytes: bytes, private_key_hex: str) -> str:
    """
    Signe des bytes arbitraires avec la clé privée Ed25519.

    Utilisé pour signer aussi bien les licences que les bundles de règles.
    Retourne la signature encodée en base64url.
    """
    try:
        from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
    except ImportError as e:
        raise LicenseError("Le package `cryptography` est requis") from e

    private_key = Ed25519PrivateKey.from_private_bytes(bytes.fromhex(private_key_hex))
    signature = private_key.sign(payload_bytes)
    return _b64url_encode(signature)


def verify_payload(payload_bytes: bytes, signature_b64: str, public_key_hex: str | None = None) -> None:
    """
    Vérifie qu'une signature Ed25519 correspond à un payload.

    Utilisé pour vérifier aussi bien les licences que les bundles de règles.
    Lève LicenseInvalidSignature si la signature est invalide.
    """
    pub_hex = (public_key_hex or PUBLIC_KEY_HEX).strip()
    if not pub_hex or pub_hex == "00" * 32:
        raise LicenseError(
            "Clé publique d'éditeur non configurée. "
            "Lancez `python scripts/generate_license_keypair.py`."
        )

    try:
        signature_bytes = _b64url_decode(signature_b64)
    except Exception as e:
        raise LicenseFormatError(f"Signature base64 invalide : {e}") from e

    try:
        from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
        public_key = Ed25519PublicKey.from_public_bytes(bytes.fromhex(pub_hex))
        public_key.verify(signature_bytes, payload_bytes)
    except ImportError as e:
        raise LicenseError(
            "Le package `cryptography` est requis pour vérifier les signatures."
        ) from e
    except Exception as e:
        raise LicenseInvalidSignature(f"Signature invalide : {e}") from e


def generate_keypair() -> tuple[str, str]:
    """
    Génère une nouvelle paire de clés Ed25519.

    Returns:
        (private_key_hex, public_key_hex) — 64 caractères hex chacun

    Usage typique :
        priv, pub = generate_keypair()
        print("Clé privée (à garder secrète) :", priv)
        print("Clé publique (à embarquer dans le code) :", pub)
    """
    try:
        from cryptography.hazmat.primitives import serialization
        from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
    except ImportError as e:
        raise LicenseError("Le package `cryptography` est requis") from e

    private_key = Ed25519PrivateKey.generate()

    private_bytes = private_key.private_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PrivateFormat.Raw,
        encryption_algorithm=serialization.NoEncryption(),
    )
    public_bytes = private_key.public_key().public_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PublicFormat.Raw,
    )

    return (private_bytes.hex(), public_bytes.hex())


# ─── Helpers base64url ──────────────────────────────────────────────────────


def _b64url_encode(data: bytes) -> str:
    """Encode en base64url sans padding."""
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def _b64url_decode(s: str) -> bytes:
    """Décode du base64url avec padding automatique."""
    pad = 4 - (len(s) % 4)
    if pad and pad < 4:
        s = s + "=" * pad
    return base64.urlsafe_b64decode(s.encode("ascii"))


def _parse_iso(s: str) -> datetime:
    """Parse une date ISO 8601 en datetime UTC-aware."""
    # Gérer le suffixe Z et les timezones
    if s.endswith("Z"):
        s = s[:-1] + "+00:00"
    dt = datetime.fromisoformat(s)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt
