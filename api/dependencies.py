"""
Dépendances FastAPI partagées entre les routers.

TODO: implémenter get_current_user, get_db, get_settings.
"""
from __future__ import annotations

# TODO: from fastapi import Depends, HTTPException, status
# TODO: from fastapi.security import OAuth2PasswordBearer
# TODO: from sqlalchemy.ext.asyncio import AsyncSession


async def get_current_user():
    """Dépendance : récupère l'utilisateur connecté depuis le JWT."""
    raise NotImplementedError


async def get_db():
    """Dépendance : session BDD async (SQLAlchemy)."""
    raise NotImplementedError


async def require_agent_role(user=None):
    """Dépendance : vérifie que l'utilisateur est un agent habilité."""
    raise NotImplementedError
