"""
Configuration centralisée via Pydantic Settings.
Toutes les valeurs sont chargées depuis les variables d'environnement.
"""
from __future__ import annotations
from enum import Enum
from functools import lru_cache
from pydantic_settings import BaseSettings


class AppEnv(str, Enum):
    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"


class Settings(BaseSettings):
    # App
    app_env: AppEnv = AppEnv.DEVELOPMENT
    app_secret_key: str = ""  # OBLIGATOIRE — définir dans .env (APP_SECRET_KEY)
    app_debug: bool = True
    app_host: str = "0.0.0.0"
    app_port: int = 8000

    # Base de données
    database_url: str = "postgresql+asyncpg://user:password@localhost:5432/carte_grise"
    database_pool_size: int = 10

    # Redis
    redis_url: str = "redis://localhost:6379/0"

    # Storage
    storage_backend: str = "local"
    storage_local_path: str = "./data/documents"

    # OCR
    ocr_provider: str = "google_docai"
    ocr_confidence_threshold: float = 0.70

    # Google Document AI
    google_project_id: str = ""
    google_location: str = "eu"
    google_docai_processor_id: str = ""
    google_application_credentials: str = ""

    # LLM
    llm_provider: str = "anthropic"
    anthropic_api_key: str = ""

    # INSEE
    insee_api_key: str = ""

    # SIV
    siv_api_url: str = ""
    siv_api_key: str = ""
    siv_habilitation_id: str = ""
    siv_environment: str = "sandbox"

    # Stripe
    stripe_secret_key: str = ""
    stripe_webhook_secret: str = ""

    # Twilio SMS
    twilio_account_sid: str = ""
    twilio_auth_token: str = ""
    twilio_phone_number: str = ""

    # Email SMTP
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""
    smtp_from_email: str = "noreply@autodocpro.fr"

    # JWT
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_minutes: int = 60

    # Rate limiting
    rate_limit_per_minute: int = 60

    # Celery
    celery_broker_url: str = "redis://localhost:6379/1"
    celery_result_backend: str = "redis://localhost:6379/2"

    # Monitoring
    sentry_dsn: str = ""
    log_level: str = "INFO"

    class Config:
        env_file = ".env"
        case_sensitive = False


@lru_cache
def get_settings() -> Settings:
    return Settings()
