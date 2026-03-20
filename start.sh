#!/bin/bash
# ============================================
# Démarrage Carte Grise Auto
# Une seule commande pour tout lancer
# ============================================

PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$PROJECT_DIR"

echo "============================================"
echo "  Démarrage Carte Grise Auto"
echo "============================================"
echo ""

# 1. PostgreSQL
brew services start postgresql@17 2>/dev/null || true
echo "✓ PostgreSQL"

# 2. Ollama
if ! curl -s http://127.0.0.1:11434/api/tags &>/dev/null; then
    ollama serve &>/dev/null &
    echo "Attente d'Ollama..."
    for i in $(seq 1 30); do
        if curl -s http://127.0.0.1:11434/api/tags &>/dev/null; then
            break
        fi
        sleep 2
    done
fi
echo "✓ Ollama"

# 3. Activer l'environnement Python
source venv/bin/activate

# 4. Lancer le polling email en arrière-plan (surveillance automatique)
mkdir -p "$PROJECT_DIR/logs"
EMAIL_LOG="$PROJECT_DIR/logs/email_poll.log"

# Vérifier si un email est configuré
CURRENT_EMAIL=$(grep "^IMAP_USER=" .env 2>/dev/null | cut -d= -f2)
if [ -n "$CURRENT_EMAIL" ] && [ "$CURRENT_EMAIL" != "votre_email@gmail.com" ]; then
    python3 -c "
import sys; sys.path.insert(0, '.')
from src.pipeline.email_loop import run_email_loop
run_email_loop(auto_send=False, poll_interval=120)
" > "$EMAIL_LOG" 2>&1 &
    EMAIL_PID=$!
    echo "✓ Surveillance email activée (polling toutes les 2 min, log: logs/email_poll.log)"
else
    EMAIL_PID=""
    echo "⚠ Email non configuré — mode import manuel uniquement"
fi

# 5. Lancer OpenClaw en arrière-plan (rédaction emails + assistance IA)
export PATH="$HOME/.npm-global/bin:$PATH"
OPENCLAW_PID=""
if command -v openclaw &>/dev/null; then
    OPENCLAW_LOG="$PROJECT_DIR/logs/openclaw.log"
    openclaw start > "$OPENCLAW_LOG" 2>&1 &
    OPENCLAW_PID=$!
    sleep 3
    if kill -0 $OPENCLAW_PID 2>/dev/null; then
        echo "✓ OpenClaw démarré (rédaction emails automatique)"
    else
        echo "⚠ OpenClaw n'a pas pu démarrer — rédaction emails manuelle"
        OPENCLAW_PID=""
    fi
else
    echo "⚠ OpenClaw non trouvé — rédaction emails manuelle"
fi

# 6. Récupérer l'IP locale
IP=$(ipconfig getifaddr en0 2>/dev/null || echo "localhost")

echo ""
echo "============================================"
echo "  Tout est lancé !"
echo "============================================"
echo ""
echo "  Dashboard : http://localhost:8501"
echo "  Depuis un autre appareil : http://${IP}:8501"
echo ""
echo "  Appuie sur Ctrl+C pour tout arrêter"
echo ""

# 6. Ouvrir le navigateur automatiquement
sleep 2
open "http://localhost:8501"

# Streamlit en premier plan (Ctrl+C arrête tout)
trap "[ -n \"$EMAIL_PID\" ] && kill $EMAIL_PID 2>/dev/null; [ -n \"$OPENCLAW_PID\" ] && kill $OPENCLAW_PID 2>/dev/null; openclaw stop 2>/dev/null; echo ''; echo 'Arrêt du système.'; exit 0" INT TERM
streamlit run dashboard/app.py
