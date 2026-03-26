"""
Gestionnaire de stockage des fichiers documents.

Backends :
- Local (développement)
- AWS S3 (production)

Tous les fichiers sont organisés par dossier :
  {dossier_id}/{document_id}/{filename}

SHA-256 calculé à l'upload pour intégrité + dédoublonnage.
"""
from __future__ import annotations

import hashlib
import os
from abc import ABC, abstractmethod
from pathlib import Path

import aiofiles


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

    @staticmethod
    def compute_sha256(file_bytes: bytes) -> str:
        return hashlib.sha256(file_bytes).hexdigest()


class LocalDocumentStore(BaseDocumentStore):
    """Backend local — développement uniquement."""

    def __init__(self, base_path: str = "./data/documents") -> None:
        self.base_path = Path(base_path)
        self.base_path.mkdir(parents=True, exist_ok=True)

    async def save(self, file_bytes: bytes, path: str, mime_type: str) -> str:
        full_path = self.base_path / path
        full_path.parent.mkdir(parents=True, exist_ok=True)
        async with aiofiles.open(full_path, "wb") as f:
            await f.write(file_bytes)
        return path

    async def get(self, path: str) -> bytes:
        full_path = self.base_path / path
        if not full_path.exists():
            raise FileNotFoundError(f"Document not found: {path}")
        async with aiofiles.open(full_path, "rb") as f:
            return await f.read()

    async def delete(self, path: str) -> None:
        full_path = self.base_path / path
        if full_path.exists():
            full_path.unlink()


class S3DocumentStore(BaseDocumentStore):
    """Backend AWS S3 — production."""

    def __init__(self, bucket: str, region: str = "eu-west-3") -> None:
        self.bucket = bucket
        self.region = region
        self._client = None

    def _get_client(self):
        if self._client is None:
            import boto3
            self._client = boto3.client("s3", region_name=self.region)
        return self._client

    async def save(self, file_bytes: bytes, path: str, mime_type: str) -> str:
        import asyncio
        client = self._get_client()
        await asyncio.get_event_loop().run_in_executor(
            None,
            lambda: client.put_object(
                Bucket=self.bucket,
                Key=path,
                Body=file_bytes,
                ContentType=mime_type,
                ServerSideEncryption="AES256",
            ),
        )
        return path

    async def get(self, path: str) -> bytes:
        import asyncio
        client = self._get_client()
        response = await asyncio.get_event_loop().run_in_executor(
            None,
            lambda: client.get_object(Bucket=self.bucket, Key=path),
        )
        return response["Body"].read()

    async def delete(self, path: str) -> None:
        import asyncio
        client = self._get_client()
        await asyncio.get_event_loop().run_in_executor(
            None,
            lambda: client.delete_object(Bucket=self.bucket, Key=path),
        )


def get_document_store() -> BaseDocumentStore:
    """Factory — retourne le store selon la config."""
    from config.settings import get_settings
    settings = get_settings()
    if settings.storage_backend == "s3":
        return S3DocumentStore(bucket="carte-grise-documents-saas", region="eu-west-3")
    return LocalDocumentStore(settings.storage_local_path)
