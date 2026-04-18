"""
Stockage local chiffré des documents — version locale d'Imatra.

Tous les documents sont stockés sur le disque local de l'agent, chiffrés
avec une clé symétrique générée à l'installation. La clé est conservée
dans un fichier de configuration local et n'est jamais transmise à l'éditeur.

Architecture :
  data/documents/{dossier_id}/{document_id}.bin   <-- fichier chiffré
  data/.encryption_key                            <-- clé symétrique (chmod 600)

Aucune dépendance cloud (S3, GCS, etc.).
"""
from __future__ import annotations

import hashlib
import os
import secrets
from pathlib import Path

import aiofiles
from cryptography.fernet import Fernet


class LocalEncryptedStore:
    """
    Store local chiffré symétriquement (Fernet / AES-128 + HMAC).

    La clé est générée au premier démarrage et persistée localement.
    L'agent est seul détenteur de cette clé — l'éditeur n'y a jamais accès.
    """

    def __init__(self, base_path: str = "./data/documents") -> None:
        self.base_path = Path(base_path)
        self.base_path.mkdir(parents=True, exist_ok=True)
        self._fernet: Fernet | None = None
        self._key_path = self.base_path.parent / ".encryption_key"

    def _ensure_key(self) -> Fernet:
        """Charge la clé existante ou en génère une nouvelle."""
        if self._fernet is not None:
            return self._fernet

        if self._key_path.exists():
            key = self._key_path.read_bytes()
        else:
            key = Fernet.generate_key()
            self._key_path.parent.mkdir(parents=True, exist_ok=True)
            self._key_path.write_bytes(key)
            try:
                os.chmod(self._key_path, 0o600)  # Lecture/écriture utilisateur seul
            except OSError:
                pass  # Windows ne supporte pas chmod de la même manière

        self._fernet = Fernet(key)
        return self._fernet

    @staticmethod
    def compute_sha256(file_bytes: bytes) -> str:
        return hashlib.sha256(file_bytes).hexdigest()

    async def save(self, file_bytes: bytes, path: str, mime_type: str = "") -> str:
        """
        Chiffre puis sauvegarde un fichier.

        Args:
            file_bytes: contenu binaire du fichier
            path: chemin logique relatif (ex: "{dossier_id}/{document_id}.bin")
            mime_type: ignoré (gardé pour compatibilité d'interface)

        Returns:
            Le chemin logique du fichier sauvegardé
        """
        fernet = self._ensure_key()
        encrypted = fernet.encrypt(file_bytes)

        full_path = self.base_path / path
        full_path.parent.mkdir(parents=True, exist_ok=True)
        async with aiofiles.open(full_path, "wb") as f:
            await f.write(encrypted)
        return path

    async def get(self, path: str) -> bytes:
        """Récupère et déchiffre un fichier."""
        full_path = self.base_path / path
        if not full_path.exists():
            raise FileNotFoundError(f"Document not found: {path}")

        fernet = self._ensure_key()
        async with aiofiles.open(full_path, "rb") as f:
            encrypted = await f.read()
        return fernet.decrypt(encrypted)

    async def delete(self, path: str) -> None:
        """Supprime un fichier (RGPD)."""
        full_path = self.base_path / path
        if full_path.exists():
            full_path.unlink()


_store: LocalEncryptedStore | None = None


def get_document_store() -> LocalEncryptedStore:
    """Factory — retourne l'instance unique du store local chiffré."""
    global _store
    if _store is None:
        from config.settings import get_settings
        settings = get_settings()
        _store = LocalEncryptedStore(settings.storage_path)
    return _store
