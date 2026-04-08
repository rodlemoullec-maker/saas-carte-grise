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


async def get_current_agent(db: DBSession) -> Professionnel:
    """
    Récupère l'agent local courant. Crée un agent vide à la volée si aucun
    n'existe — la version locale d'Imatra n'exige plus de profil agent
    rempli pour fonctionner (cf. décision produit avril 2026).
    """
    from sqlalchemy import select
    result = await db.execute(select(Professionnel).limit(1))
    agent = result.scalar_one_or_none()
    if agent is None:
        agent = Professionnel(
            raison_sociale="(Mon cabinet)",
            email="agent@local",
            setup_complete=True,  # toujours True : profil désormais facultatif
        )
        db.add(agent)
        await db.flush()
    return agent
