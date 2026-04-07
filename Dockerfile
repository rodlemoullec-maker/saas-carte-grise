# AutoDoc Pro — Image locale (logiciel installé chez l'agent habilité SIV)
#
# Multi-stage build :
#   1. node-build : compile le frontend React/Vite en fichiers statiques
#   2. python-runtime : image finale FastAPI + PaddleOCR + frontend statique
#
# Le résultat est une seule image qui sert tout sur le port 8001 :
#   - Backend FastAPI : /docs, /dossiers/*, /agent, /license/*, /rules/*, etc.
#   - Frontend React  : /, /assets/*, etc. (servi en statique)
#
# L'agent fait :
#     docker compose up -d
#     → ouvrir http://localhost:8001 dans son navigateur
#
# Aucun appel cloud n'est effectué pendant le runtime, à l'exception des
# vérifications optionnelles de licence et de mise à jour des règles.

# ═══════════════════════════════════════════════════════════════════════════
# STAGE 1 : Build du frontend React/Vite
# ═══════════════════════════════════════════════════════════════════════════
FROM node:20-alpine AS node-build

WORKDIR /build

# Installer les dépendances en premier (cache Docker)
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci --silent

# Copier le code source et builder
COPY frontend/ ./
RUN npm run build
# → produit /build/dist/index.html + /build/dist/assets/*


# ═══════════════════════════════════════════════════════════════════════════
# STAGE 2 : Image runtime Python avec FastAPI et PaddleOCR
# ═══════════════════════════════════════════════════════════════════════════
FROM python:3.11-slim AS runtime

# Métadonnées
LABEL org.opencontainers.image.title="AutoDoc Pro"
LABEL org.opencontainers.image.description="Logiciel local de préparation de dossiers carte grise pour agents habilités SIV"
LABEL org.opencontainers.image.version="2.0.0-local"
LABEL org.opencontainers.image.vendor="AutoDoc Pro"

WORKDIR /app

# ─── Dépendances système nécessaires ────────────────────────────────────
# - poppler-utils : conversion PDF → image (utilisé par pdf2image)
# - libgomp1     : runtime OpenMP requis par PaddleOCR
# - libgl1       : OpenGL bindings (requis par OpenCV / PaddleOCR)
# - libglib2.0-0 : requis par OpenCV
# - ca-certificates : pour les vérifications HTTPS (licences, MAJ règles)
# - tini         : init léger pour gérer les signaux SIGTERM proprement
RUN apt-get update && apt-get install -y --no-install-recommends \
    poppler-utils \
    libgomp1 \
    libgl1 \
    libglib2.0-0 \
    ca-certificates \
    tini \
    && rm -rf /var/lib/apt/lists/*

# ─── Dépendances Python ────────────────────────────────────────────────
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

# ─── Code source backend ───────────────────────────────────────────────
COPY api/ ./api/
COPY engine/ ./engine/
COPY integrations/ ./integrations/
COPY notifications/ ./notifications/
COPY storage/ ./storage/
COPY config/ ./config/

# ─── Frontend buildé depuis le stage précédent ─────────────────────────
COPY --from=node-build /build/dist ./frontend/dist

# ─── Configuration runtime ─────────────────────────────────────────────
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    APP_HOST=0.0.0.0 \
    APP_PORT=8001 \
    DATABASE_URL=sqlite+aiosqlite:////app/data/autodoc_pro.db \
    STORAGE_PATH=/app/data/documents \
    OCR_PROVIDER=paddle

# Le volume /app/data contient :
#   - autodoc_pro.db        (SQLite)
#   - documents/            (documents chiffrés Fernet)
#   - .license/             (license.key + trial_started.json)
#   - .encryption_key       (clé Fernet du store)
#   - rules/current.json    (bundle de règles signé)
#   - logs/
VOLUME /app/data

EXPOSE 8001

# Healthcheck : vérifier que /health répond
HEALTHCHECK --interval=30s --timeout=5s --start-period=30s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8001/health', timeout=3)" || exit 1

# tini comme init pour gérer SIGTERM proprement (Ctrl+C, docker stop)
ENTRYPOINT ["/usr/bin/tini", "--"]
CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8001"]
