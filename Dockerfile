FROM python:3.12-slim

WORKDIR /app

# Dépendances système
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1-mesa-glx \
    libglib2.0-0 \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Dépendances Python
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Code application
COPY config/ config/
COPY src/ src/
COPY dashboard/ dashboard/
COPY scripts/ scripts/
COPY templates/ templates/
COPY skills/ skills/

# Créer les répertoires de données
RUN mkdir -p data/dossiers data/output data/types_mines

# Port Streamlit
EXPOSE 8501
# Port FastAPI
EXPOSE 8000

CMD ["streamlit", "run", "dashboard/app.py", "--server.headless", "true", "--server.port", "8501", "--server.address", "0.0.0.0"]
