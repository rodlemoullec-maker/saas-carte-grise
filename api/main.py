"""
Application FastAPI principale — Imatra local.

Logiciel installé localement chez l'agent habilité SIV.
Aucune dépendance à un service cloud (sauf vérification de licence
et téléchargement des règles V-XX/C-XX à jour).
"""
from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.routers import clients, decisions, documents, dossiers, emails, license as license_router, professionnel, rules
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
    logger.info("[Startup] Imatra local prêt sur http://%s:%s", _settings.app_host, _settings.app_port)
    yield


app = FastAPI(
    title="Imatra — Local",
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
app.include_router(professionnel.router)   # prefix="/agent" déjà défini
app.include_router(emails.router)          # prefix="/emails" déjà défini
app.include_router(license_router.router)  # prefix="/license" déjà défini
app.include_router(rules.router)           # prefix="/rules" déjà défini
app.include_router(clients.router)         # prefix="/clients" déjà défini


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
        "service": "Imatra",
        "version": "2.0.0-local",
        "mode": "local",
        "description": (
            "Logiciel installé localement chez l'agent habilité SIV. "
            "Aucune donnée client ne quitte cette machine. "
            "L'éditeur (Imatra) ne traite aucune donnée personnelle."
        ),
        "responsabilite": (
            "L'agent habilité SIV est seul responsable de la conformité des dossiers "
            "soumis au SIV. Imatra est un outil d'aide à la décision."
        ),
    }


# ─── Frontend statique (production Docker uniquement) ───────────────────
#
# En développement, le frontend tourne séparément sur Vite (port 5173) avec
# un proxy vers /api → http://127.0.0.1:8001. En production / dans Docker,
# le frontend buildé est copié dans frontend/dist et servi directement par
# FastAPI sur la racine /.
#
# Cette section est conditionnelle : elle ne s'active que si le dossier
# frontend/dist existe au démarrage.
from pathlib import Path

_frontend_dist = Path(__file__).parent.parent / "frontend" / "dist"
if _frontend_dist.is_dir():
    from fastapi.responses import FileResponse
    from fastapi.staticfiles import StaticFiles

    # Servir les assets buildés (JS, CSS, images) sous /assets
    _assets_dir = _frontend_dist / "assets"
    if _assets_dir.is_dir():
        app.mount("/assets", StaticFiles(directory=_assets_dir), name="assets")

    # Servir les fichiers à la racine (favicon, manifest, etc.)
    _index = _frontend_dist / "index.html"

    @app.get("/", include_in_schema=False)
    async def serve_index():
        return FileResponse(_index)

    # Catch-all pour le routing client React (SPA)
    # Toute route non matchée par une API renvoie index.html — le routeur
    # React prend ensuite le relais côté navigateur.
    @app.get("/{full_path:path}", include_in_schema=False)
    async def serve_spa(full_path: str):
        # Si c'est un fichier réel à la racine de dist (favicon, robots.txt…)
        candidate = _frontend_dist / full_path
        if candidate.is_file():
            return FileResponse(candidate)
        return FileResponse(_index)

    logger.info(f"[Startup] Frontend statique servi depuis {_frontend_dist}")
else:
    logger.info(
        "[Startup] frontend/dist absent — mode développement "
        "(lancez 'npm run dev' dans frontend/ pour servir l'UI)"
    )
