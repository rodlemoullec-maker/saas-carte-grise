#!/bin/bash
# ============================================
# Script d'installation — Carte Grise Auto
# Pour Mac Apple Silicon (M1/M2/M3/M4)
# ============================================

set -e

PROJECT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$PROJECT_DIR"

echo "============================================"
echo "  Installation Carte Grise Auto"
echo "  Répertoire : $PROJECT_DIR"
echo "============================================"
echo ""

# --- Détecter la RAM ---
RAM_GB=$(sysctl -n hw.memsize 2>/dev/null | awk '{print int($1/1073741824)}')
echo "RAM détectée : ${RAM_GB} GB"

if [ "$RAM_GB" -ge 48 ]; then
    MODEL_TEXT="qwen2.5:32b"
elif [ "$RAM_GB" -ge 24 ]; then
    MODEL_TEXT="qwen2.5:14b"
else
    MODEL_TEXT="qwen2.5:7b"
fi
MODEL_VISION="qwen2.5vl:7b"
echo "Modèle texte : $MODEL_TEXT"
echo "Modèle vision : $MODEL_VISION"
echo ""

# --- 1. Homebrew ---
if ! command -v brew &> /dev/null; then
    echo "Installation de Homebrew..."
    /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
fi
echo "✓ Homebrew"

# --- 2. Python ---
if ! command -v python3 &> /dev/null; then
    echo "Installation de Python..."
    brew install python
fi
echo "✓ Python $(python3 --version)"

# --- 3. Node.js ---
if ! command -v node &> /dev/null; then
    echo "Installation de Node.js..."
    brew install node
fi
echo "✓ Node.js $(node --version)"

# --- 4. PostgreSQL ---
if ! command -v psql &> /dev/null; then
    echo "Installation de PostgreSQL..."
    brew install postgresql@17
    echo 'export PATH="/opt/homebrew/opt/postgresql@17/bin:$PATH"' >> ~/.zshrc
    export PATH="/opt/homebrew/opt/postgresql@17/bin:$PATH"
fi
brew services start postgresql@17 2>/dev/null || true
echo "✓ PostgreSQL"

# --- 5. Ollama ---
if ! command -v ollama &> /dev/null; then
    echo "Installation d'Ollama..."
    brew install ollama
fi
ollama serve &>/dev/null &
sleep 3
echo "✓ Ollama"

# --- 6. Environnement Python ---
if [ ! -d "venv" ]; then
    echo "Création de l'environnement virtuel Python..."
    python3 -m venv venv
fi
source venv/bin/activate
pip install --upgrade pip -q
pip install -r requirements.txt -q 2>/dev/null
pip install surya-ocr --no-deps -q 2>/dev/null
pip install torch torchvision --no-deps -q 2>/dev/null
pip install transformers --no-deps -q 2>/dev/null
pip install regex pydantic-settings platformdirs pypdfium2 peft boto3 -q 2>/dev/null
echo "✓ Dépendances Python"

# --- 7. Base de données ---
export PATH="/opt/homebrew/opt/postgresql@17/bin:$PATH"
createdb carte_grise 2>/dev/null || true
python3 scripts/setup_db.py
echo "✓ Base de données"

# --- 8. Import base véhicules (neufs + occasions) ---
mkdir -p data/types_mines

# 8a. Véhicules neufs (ADEME Car Labelling)
if [ ! -f "data/types_mines/ademe_car_labelling.csv" ]; then
    echo "Téléchargement base véhicules neufs..."
    curl -sL -o data/types_mines/ademe_car_labelling.csv \
        "https://www.data.gouv.fr/api/1/datasets/r/669a1f00-299f-4c7c-9db2-cd32401e7b25"
fi
python3 scripts/import_types_mines.py 2>/dev/null || true
echo "✓ Base véhicules neufs importée"

# 8b. Véhicules occasions (ADEME historique 2012-2015)
echo "Téléchargement base véhicules occasions (2012-2015)..."

# 2015 (ZIP)
if [ ! -f "data/types_mines/tmp_2015/fic_etiq_edition_40-mars-2015.csv" ]; then
    curl -sL -o data/types_mines/ademe_2015.zip \
        "https://www.data.gouv.fr/fr/datasets/r/bc42c2e3-d24c-4499-a966-d35656c6cfc1"
    mkdir -p data/types_mines/tmp_2015
    unzip -o data/types_mines/ademe_2015.zip -d data/types_mines/tmp_2015 -q 2>/dev/null || true
fi

# 2014 (ZIP déguisé en CSV)
if [ ! -d "data/types_mines/tmp_2014" ]; then
    curl -sL -o data/types_mines/ademe_2014.zip \
        "https://www.data.gouv.fr/fr/datasets/r/da84abee-6038-43ea-b316-cdaea2514f66"
    mkdir -p data/types_mines/tmp_2014
    unzip -o data/types_mines/ademe_2014.zip -d data/types_mines/tmp_2014 -q 2>/dev/null || true
fi

# 2013 (ZIP déguisé en CSV)
if [ ! -d "data/types_mines/tmp_2013" ]; then
    curl -sL -o data/types_mines/ademe_2013.zip \
        "https://www.data.gouv.fr/fr/datasets/r/6ff09b59-84ca-4346-a8d1-3587ed94da15"
    mkdir -p data/types_mines/tmp_2013
    unzip -o data/types_mines/ademe_2013.zip -d data/types_mines/tmp_2013 -q 2>/dev/null || true
fi

# 2012 (ZIP déguisé en CSV)
if [ ! -d "data/types_mines/tmp_2012" ]; then
    curl -sL -o data/types_mines/ademe_2012.zip \
        "https://www.data.gouv.fr/fr/datasets/r/b6c87a29-2df0-4e23-8837-1a71cdf254b9"
    mkdir -p data/types_mines/tmp_2012
    unzip -o data/types_mines/ademe_2012.zip -d data/types_mines/tmp_2012 -q 2>/dev/null || true
fi

python3 scripts/import_historique.py 2>/dev/null || true
echo "✓ Base véhicules occasions importée (84 000+ modèles)"

# --- 9. Modèles IA ---
echo "Téléchargement des modèles IA (peut prendre plusieurs minutes)..."
ollama pull "$MODEL_TEXT"
ollama pull "$MODEL_VISION"
echo "✓ Modèles IA"

# --- 10. OpenClaw ---
if ! command -v openclaw &> /dev/null; then
    echo "Installation d'OpenClaw..."
    mkdir -p ~/.npm-global
    npm config set prefix "$HOME/.npm-global"
    export PATH="$HOME/.npm-global/bin:$PATH"
    npm install -g openclaw -q
    echo 'export PATH="$HOME/.npm-global/bin:$PATH"' >> ~/.zshrc
fi
echo "✓ OpenClaw $(openclaw --version 2>/dev/null || echo 'installé')"

# --- 11. Configuration OpenClaw ---
bash scripts/setup_openclaw.sh
echo "✓ OpenClaw configuré"

# --- 12. Fichier .env ---
if [ ! -f ".env" ]; then
    cp .env.example .env

    echo ""
    echo "=== Configuration email ==="
    read -p "Serveur IMAP (ex: imap.gmail.com) : " imap_srv
    read -p "Adresse email : " imap_user
    read -sp "Mot de passe application : " imap_pass
    echo ""

    sed -i '' "s|IMAP_SERVER=.*|IMAP_SERVER=${imap_srv}|" .env
    sed -i '' "s|IMAP_USER=.*|IMAP_USER=${imap_user}|" .env
    sed -i '' "s|IMAP_PASSWORD=.*|IMAP_PASSWORD=${imap_pass}|" .env
    sed -i '' "s|MODEL_TEXT=.*|MODEL_TEXT=${MODEL_TEXT}|" .env
    sed -i '' "s|MODEL_VISION=.*|MODEL_VISION=${MODEL_VISION}|" .env
    sed -i '' "s|DB_USER=.*|DB_USER=$(whoami)|" .env
    sed -i '' "s|DB_HOST=.*|DB_HOST=localhost|" .env
    sed -i '' "s|DB_PASSWORD=.*|DB_PASSWORD=|" .env

    echo "✓ Configuration sauvegardée"
fi

# --- 13. Streamlit accessible réseau ---
mkdir -p .streamlit
cat > .streamlit/config.toml << 'TOML'
[server]
headless = true
address = "0.0.0.0"
port = 8501

[browser]
gatherUsageStats = false
TOML
echo "✓ Streamlit configuré (accessible réseau)"

echo ""
echo "============================================"
echo "  Installation terminée !"
echo "============================================"
echo ""
echo "=== Utilisation sur CE Mac ==="
echo "  source venv/bin/activate"
echo "  streamlit run dashboard/app.py"
echo "  → Dashboard : http://localhost:8501"
echo ""
echo "=== Accès depuis un portable ==="
echo "  1. Même réseau WiFi :"
echo "     → http://$(ipconfig getifaddr en0 2>/dev/null || echo 'IP_DU_MAC'):8501"
echo ""
echo "  2. À distance (autre réseau) :"
echo "     → Installer Tailscale sur les 2 machines (gratuit)"
echo "     → Ou tunnel SSH : ssh -L 8501:localhost:8501 user@mac"
echo ""
echo "  3. OpenClaw depuis le portable :"
echo "     → Installer openclaw sur le portable"
echo "     → Configurer en mode remote (voir docs/06_acces_distant.md)"
echo ""
