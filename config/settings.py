"""
Configuration centralisée — version locale d'Imatra.

Toutes les valeurs sont chargées depuis les variables d'environnement
ou utilisent leurs valeurs par défaut adaptées à un déploiement local.

En version locale, l'application tourne entièrement sur la machine
de l'agent. Aucune dépendance à un service cloud n'est nécessaire.
"""
from __future__ import annotations
from enum import Enum
from functools import lru_cache
from pydantic_settings import BaseSettings


class AppEnv(str, Enum):
    DEVELOPMENT = "development"
    PRODUCTION = "production"


class Settings(BaseSettings):
    # ───────────────────────────────────────────────
    # Application
    # ───────────────────────────────────────────────
    app_env: AppEnv = AppEnv.PRODUCTION
    app_secret_key: str = "local-default-change-me"  # Généré au premier démarrage
    app_debug: bool = False
    app_host: str = "127.0.0.1"  # Local uniquement
    app_port: int = 8001

    # ───────────────────────────────────────────────
    # Base de données — SQLite locale
    # ───────────────────────────────────────────────
    database_url: str = "sqlite+aiosqlite:///./data/imatra.db"
    database_pool_size: int = 5  # Ignoré pour SQLite

    # ───────────────────────────────────────────────
    # Stockage local des documents (chiffré)
    # ───────────────────────────────────────────────
    storage_path: str = "./data/documents"
    storage_encryption_key: str = ""  # Généré automatiquement au premier démarrage

    # ───────────────────────────────────────────────
    # OCR — local (PaddleOCR par défaut)
    # ───────────────────────────────────────────────
    ocr_provider: str = "paddle"  # paddle
    ocr_confidence_threshold: float = 0.70
    ocr_language: str = "fr"

    # ───────────────────────────────────────────────
    # Système de licences (seul appel cloud autorisé)
    # ───────────────────────────────────────────────
    license_server_url: str = "https://licenses.imatra.fr"
    license_check_interval_hours: int = 24
    license_offline_grace_days: int = 30

    # ───────────────────────────────────────────────
    # Mises à jour des règles V-XX/C-XX
    # ───────────────────────────────────────────────
    rules_update_url: str = "https://licenses.imatra.fr/rules/latest"
    rules_check_interval_hours: int = 24

    # ───────────────────────────────────────────────
    # Logs
    # ───────────────────────────────────────────────
    log_level: str = "INFO"
    log_path: str = "./data/logs"

    class Config:
        env_file = ".env"
        case_sensitive = False
        extra = "ignore"  # Ignorer les vieilles vars d'env de l'ère SaaS


@lru_cache
def get_settings() -> Settings:
    return Settings()
