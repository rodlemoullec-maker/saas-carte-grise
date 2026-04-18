"""
Base SQLAlchemy + session factory async.
"""
from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, func
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from config.settings import get_settings


class Base(DeclarativeBase):
    """Base déclarative commune à tous les modèles."""
    pass


class TimestampMixin:
    """Mixin ajoutant created_at / updated_at automatiques."""
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


# Engine + session (lazy init)
_engine = None
_session_factory = None


def get_engine():
    global _engine
    if _engine is None:
        settings = get_settings()
        # SQLite n'a pas de pool de connexions au sens classique
        kwargs = {"echo": settings.app_debug}
        if not settings.database_url.startswith("sqlite"):
            kwargs["pool_size"] = settings.database_pool_size
        _engine = create_async_engine(settings.database_url, **kwargs)
    return _engine


async def init_db() -> None:
    """
    Crée toutes les tables au premier démarrage.
    En version locale (SQLite), c'est appelé au lancement du logiciel
    si le fichier de base n'existe pas encore.
    """
    engine = get_engine()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


def get_session_factory() -> async_sessionmaker[AsyncSession]:
    global _session_factory
    if _session_factory is None:
        _session_factory = async_sessionmaker(
            get_engine(), class_=AsyncSession, expire_on_commit=False,
        )
    return _session_factory


async def get_db() -> AsyncSession:
    """Dependency injection FastAPI — yield une session."""
    factory = get_session_factory()
    async with factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
