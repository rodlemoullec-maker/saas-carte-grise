"""
Gestionnaire de stockage des fichiers documents.

Supporte :
- Local (développement)
- AWS S3 (production)
- Google Cloud Storage

Tous les fichiers sont chiffrés au repos.
Les chemins stockés en BDD sont des chemins logiques (jamais le chemin physique).

TODO: implémenter les trois backends.
TODO: implémenter le chiffrement AES-256 côté applicatif (en plus du chiffrement S3).
TODO: implémenter la purge automatique RGPD (délai de conservation).
"""
from __future__ import annotations
from abc import ABC, abstractmethod


class BaseDocumentStore(ABC):

    @abstractmethod
    async def save(self, file_bytes: bytes, path: str, mime_type: str) -> str:
        """Sauvegarde un fichier et retourne le chemin logique."""
        ...

    @abstractmethod
    async def get(self, path: str) -> bytes:
        """Récupère un fichier par son chemin logique."""
        ...

    @abstractmethod
    async def delete(self, path: str) -> None:
        """Supprime un fichier (RGPD)."""
        ...


class LocalDocumentStore(BaseDocumentStore):
    """Backend local — développement uniquement."""

    def __init__(self, base_path: str) -> None:
        self.base_path = base_path

    async def save(self, file_bytes: bytes, path: str, mime_type: str) -> str:
        # TODO: implémenter
        raise NotImplementedError

    async def get(self, path: str) -> bytes:
        raise NotImplementedError

    async def delete(self, path: str) -> None:
        raise NotImplementedError


class S3DocumentStore(BaseDocumentStore):
    """Backend AWS S3 — production."""

    def __init__(self, bucket: str, region: str) -> None:
        self.bucket = bucket
        self.region = region

    async def save(self, file_bytes: bytes, path: str, mime_type: str) -> str:
        # TODO: boto3 put_object avec SSE-S3
        raise NotImplementedError

    async def get(self, path: str) -> bytes:
        raise NotImplementedError

    async def delete(self, path: str) -> None:
        raise NotImplementedError
