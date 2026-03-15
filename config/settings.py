# Configuration centrale du projet Carte Grise Auto

import os
from pathlib import Path

# Chemins
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
DOSSIERS_DIR = DATA_DIR / "dossiers"
OUTPUT_DIR = DATA_DIR / "output"
TEMPLATES_DIR = BASE_DIR / "templates"
TYPES_MINES_DIR = DATA_DIR / "types_mines"

# Ollama
OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://localhost:11434")
MODEL_VISION = os.getenv("MODEL_VISION", "qwen2.5vl:7b")
MODEL_TEXT = os.getenv("MODEL_TEXT", "qwen2.5:7b")

# Email IMAP
IMAP_SERVER = os.getenv("IMAP_SERVER", "")
IMAP_PORT = int(os.getenv("IMAP_PORT", "993"))
IMAP_USER = os.getenv("IMAP_USER", "")
IMAP_PASSWORD = os.getenv("IMAP_PASSWORD", "")
EMAIL_POLL_INTERVAL = 120  # secondes

# PostgreSQL
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = int(os.getenv("DB_PORT", "5432"))
DB_NAME = os.getenv("DB_NAME", "carte_grise")
DB_USER = os.getenv("DB_USER", os.getenv("USER", "postgres"))
DB_PASSWORD = os.getenv("DB_PASSWORD", "")

DATABASE_URL = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

# CERFA
CERFA_13750_TEMPLATE = TEMPLATES_DIR / "cerfa_13750_07.pdf"
