"""
Application FastAPI principale.

Point d'entrée de l'API REST du SaaS carte grise.
"""
from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.routers import batch, decisions, documents, dossiers, webhooks

app = FastAPI(
    title="SaaS Carte Grise — API",
    description="Automatisation des demandes d'immatriculation",
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # TODO: restreindre en production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# TODO: ajouter middleware auth JWT
# TODO: ajouter middleware rate limiting
# TODO: ajouter middleware audit log

# Routers
app.include_router(dossiers.router, prefix="/dossiers", tags=["dossiers"])
app.include_router(documents.router, prefix="/documents", tags=["documents"])
app.include_router(decisions.router, prefix="/decisions", tags=["decisions"])
app.include_router(webhooks.router, prefix="/webhooks", tags=["webhooks"])
app.include_router(batch.router, prefix="/dossiers", tags=["batch"])


@app.get("/health")
async def health():
    return {"status": "ok", "version": "0.1.0"}
