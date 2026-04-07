"""
Application FastAPI principale — AutoDoc Pro local.

Logiciel installé localement chez l'agent habilité SIV.
Aucune dépendance à un service cloud (sauf vérification de licence
et téléchargement des règles V-XX/C-XX à jour).
"""
from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.routers import decisions, documents, dossiers, professionnel
from config.settings import get_settings

logger = logging.getLogger(__name__)
_settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifecycle de l'application locale.

    Au démarrage : crée les tables SQLite si elles n'existent pas.
    À l'arrêt : rien (SQLite gère tout localement).
    """
    from api.models.base import init_db
    logger.info("[Startup] Initialisation de la base SQLite locale")
    await init_db()
    logger.info("[Startup] AutoDoc Pro local prêt sur http://%s:%s", _settings.app_host, _settings.app_port)
    yield


app = FastAPI(
    title="AutoDoc Pro — Local",
    description="Logiciel local de préparation de dossiers carte grise pour agents habilités SIV",
    version="2.0.0-local",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# CORS — uniquement localhost en local
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",       # dev Vite
        "http://localhost:5174",       # dev Vite alt port
        "http://localhost:3000",       # dev alt
        "http://localhost:8001",       # serveur local
        "http://127.0.0.1:5173",
        "http://127.0.0.1:8001",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routers locaux
app.include_router(dossiers.router, prefix="/dossiers", tags=["dossiers"])
app.include_router(documents.router, prefix="/documents", tags=["documents"])
app.include_router(decisions.router, prefix="/decisions", tags=["decisions"])
app.include_router(professionnel.router)  # prefix="/agent" déjà défini dans le router


@app.get("/health")
async def health():
    return {
        "status": "ok",
        "version": "2.0.0-local",
        "mode": "local",
        "ocr_provider": _settings.ocr_provider,
    }


@app.get("/info")
async def info():
    """Informations sur l'instance locale."""
    return {
        "service": "AutoDoc Pro",
        "version": "2.0.0-local",
        "mode": "local",
        "description": (
            "Logiciel installé localement chez l'agent habilité SIV. "
            "Aucune donnée client ne quitte cette machine. "
            "L'éditeur (AutoDoc Pro) ne traite aucune donnée personnelle."
        ),
        "responsabilite": (
            "L'agent habilité SIV est seul responsable de la conformité des dossiers "
            "soumis au SIV. AutoDoc Pro est un outil d'aide à la décision."
        ),
    }
