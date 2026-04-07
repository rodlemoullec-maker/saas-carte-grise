# ─── Base commune ───────────────────────────────────────────────────────────
FROM python:3.12-slim AS base

WORKDIR /app

# Deps systeme pour Playwright, pdf2image (poppler), Pillow
RUN apt-get update && apt-get install -y --no-install-recommends \
    poppler-utils \
    libmagic1 \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Installer les navigateurs Playwright
RUN playwright install --with-deps chromium

COPY . .

# ─── API ────────────────────────────────────────────────────────────────────
FROM base AS api

EXPOSE 8000

CMD ["sh", "-c", "uvicorn api.main:app --host 0.0.0.0 --port ${PORT:-8000}"]

# ─── Dashboard Streamlit ────────────────────────────────────────────────────
FROM base AS dashboard

EXPOSE 8501

CMD ["streamlit", "run", "dashboard/app.py", "--server.port=8501", "--server.address=0.0.0.0"]

# ─── Worker Celery ──────────────────────────────────────────────────────────
FROM base AS worker

CMD ["celery", "-A", "workers.pipeline", "worker", "--loglevel=info", "--concurrency=4"]
