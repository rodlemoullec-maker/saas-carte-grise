"""
Dépendances FastAPI partagées entre les routers.

Re-export depuis les modules spécialisés pour compatibilité.
"""
from __future__ import annotations

from api.auth import get_current_pro, get_optional_pro  # noqa: F401
from api.models.base import get_db  # noqa: F401
