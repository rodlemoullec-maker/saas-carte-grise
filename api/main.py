"""
Application FastAPI principale.

Point d'entrée de l'API REST du SaaS carte grise.
"""
from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.routers import batch, client, decisions, documents, dossiers, professionnel, scan, webhooks

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
app.include_router(professionnel.router, tags=["professionnel"])
app.include_router(client.router, tags=["client"])
app.include_router(scan.router, prefix="/scan", tags=["scan"])


@app.get("/health")
async def health():
    return {"status": "ok", "version": "0.1.0"}


@app.get("/mentions-legales")
async def mentions_legales():
    """Mentions legales, CGU, CGV, politique de confidentialite."""
    return {
        "service": {
            "nom": "AutoDoc Pro",
            "description": "Service d'aide a la constitution de dossiers de carte grise pour professionnels de l'automobile.",
        },
        "donnees_personnelles": {
            "responsable_traitement": "AutoDoc Pro",
            "finalite": "Constitution de dossiers de demande d'immatriculation de vehicules",
            "base_legale": "Consentement (client) / Execution contractuelle (professionnel)",
            "sous_traitants": [
                {
                    "nom": "Google LLC",
                    "service": "Google Document AI",
                    "role": "Lecture optique des documents (OCR) — conversion image/PDF en texte brut",
                    "pays": "Etats-Unis",
                    "garanties": "Clauses contractuelles types (CCT) conformes au RGPD",
                    "retention": "Aucune retention — les donnees sont traitees en temps reel et non conservees",
                },
                {
                    "nom": "Anthropic",
                    "service": "Claude (API)",
                    "role": "Extraction et structuration des informations des documents — classification, extraction des champs, verification de coherence",
                    "pays": "Etats-Unis",
                    "garanties": "Clauses contractuelles types (CCT) conformes au RGPD",
                    "retention": "Aucune retention — Anthropic ne conserve pas les donnees envoyees via l'API et ne les utilise pas pour entrainer ses modeles",
                },
                {
                    "nom": "Neon (base de donnees)",
                    "service": "PostgreSQL heberge",
                    "role": "Stockage temporaire des dossiers en cours de traitement",
                    "pays": "Union Europeenne (Francfort)",
                    "garanties": "Donnees hebergees en UE",
                    "retention": "Documents supprimes a la finalisation du dossier — dossiers archives 5 ans (obligation legale)",
                },
            ],
            "transfert_hors_ue": (
                "Les donnees sont transferees vers les Etats-Unis uniquement pour le traitement OCR (Google) "
                "et l'extraction (Anthropic). Ces transferts sont encadres par des clauses contractuelles types (CCT) "
                "conformement a l'article 46 du RGPD. Aucune donnee n'est conservee aux Etats-Unis."
            ),
            "conservation": {
                "documents_client": "Supprimes automatiquement a la finalisation du dossier",
                "dossiers_pro": "Archives 5 ans (obligation legale)",
                "donnees_facturation": "Archives 10 ans (obligation comptable)",
            },
            "droits": {
                "acces": "Vous pouvez demander l'acces a vos donnees personnelles",
                "rectification": "Vous pouvez demander la correction de donnees inexactes",
                "suppression": "Vous pouvez demander la suppression de vos donnees",
                "portabilite": "Vous pouvez demander le transfert de vos donnees",
                "opposition": "Vous pouvez vous opposer au traitement de vos donnees",
                "contact": "rgpd@cartegrisepro.fr",
            },
            "politique_complete": "cartegrisepro.fr/confidentialite",
        },
        "cgu": {
            "limitation_responsabilite": (
                "AutoDoc Pro est un outil d'aide a la constitution de dossier. "
                "Il ne se substitue ni au professionnel habilite SIV, ni a l'administration, ni a un conseiller juridique. "
                "L'extraction automatique des donnees (OCR + IA) est realisee a titre d'aide et peut contenir des erreurs."
            ),
        },
        "cgv": {
            "tarification": "12 EUR par dossier moto, 14 EUR par dossier voiture — tarif fixe par dossier traite",
            "paiement": "Par batch de 5 dossiers maximum — paiement requis avant de continuer",
        },
    }
