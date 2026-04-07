"""
Alembic env.py — configuration pour migrations async (Neon PostgreSQL).

Charge la DATABASE_URL depuis .env via config/settings.py,
convertit asyncpg → psycopg2 pour la migration sync.
"""
from logging.config import fileConfig

from sqlalchemy import engine_from_config, pool

from alembic import context

# ─── Charger nos modeles pour autogenerate ──────────────────────────────────
from api.models.base import Base
from api.models.dossier import DossierDB  # noqa: F401
from api.models.professionnel import Professionnel  # noqa: F401
from api.models.document import DocumentDB  # noqa: F401

target_metadata = Base.metadata

# ─── Config Alembic ─────────────────────────────────────────────────────────
config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Charger la DB URL depuis nos settings (.env)
from config.settings import get_settings

settings = get_settings()
db_url = settings.database_url

# Convertir asyncpg → psycopg2 pour Alembic (sync)
sync_url = db_url.replace("postgresql+asyncpg://", "postgresql://")
# Neon utilise ?ssl=require mais psycopg2 attend ?sslmode=require
sync_url = sync_url.replace("?ssl=require", "?sslmode=require")
config.set_main_option("sqlalchemy.url", sync_url)


def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
