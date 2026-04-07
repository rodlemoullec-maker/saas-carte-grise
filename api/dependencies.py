"""
Dépendances FastAPI partagées entre les routers.

Version locale : pas d'authentification JWT cloud, l'agent est seul utilisateur
de l'instance locale. La protection est assurée par le système de licences.
"""
from __future__ import annotations

from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from api.models.base import get_db
from api.models.professionnel import Professionnel


# Type alias pour les routes FastAPI
DBSession = Annotated[AsyncSession, Depends(get_db)]


async def get_current_agent(db: DBSession) -> Professionnel | None:
    """
    Récupère l'agent local courant.

    En version locale, il y a un seul Professionnel (l'agent qui possède
    cette installation). On retourne celui-là.
    """
    from sqlalchemy import select
    result = await db.execute(select(Professionnel).limit(1))
    return result.scalar_one_or_none()
