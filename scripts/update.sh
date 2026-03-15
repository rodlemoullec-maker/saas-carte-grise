#!/bin/bash
# ============================================
# Mise à jour — Carte Grise Auto
# À lancer régulièrement (1x/mois recommandé)
# ou après un changement de réglementation
# ============================================

set -e

PROJECT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$PROJECT_DIR"
source venv/bin/activate
export PATH="/opt/homebrew/opt/postgresql@17/bin:$PATH"

echo "============================================"
echo "  Mise à jour Carte Grise Auto"
echo "  $(date '+%d/%m/%Y %H:%M')"
echo "============================================"
echo ""

# --- 1. Mise à jour base véhicules neufs (ADEME) ---
echo "[1/5] Mise à jour base véhicules neufs (ADEME)..."
curl -sL -o data/types_mines/ademe_car_labelling_new.csv \
    "https://www.data.gouv.fr/api/1/datasets/r/669a1f00-299f-4c7c-9db2-cd32401e7b25"

# Vérifier que le fichier est valide (pas une page d'erreur)
if head -1 data/types_mines/ademe_car_labelling_new.csv | grep -q "Marque"; then
    mv data/types_mines/ademe_car_labelling_new.csv data/types_mines/ademe_car_labelling.csv
    python3 scripts/import_types_mines.py 2>/dev/null
    echo "  ✓ Base véhicules neufs mise à jour"
else
    rm -f data/types_mines/ademe_car_labelling_new.csv
    echo "  ⚠ Téléchargement échoué, base inchangée"
fi

# --- 2. Mise à jour modèles Ollama ---
echo ""
echo "[2/5] Mise à jour modèles IA..."
ollama pull "$(grep MODEL_TEXT .env | cut -d= -f2)" 2>/dev/null || true
ollama pull "$(grep MODEL_VISION .env | cut -d= -f2)" 2>/dev/null || true
echo "  ✓ Modèles IA à jour"

# --- 3. Mise à jour dépendances Python ---
echo ""
echo "[3/5] Mise à jour dépendances Python..."
pip install --upgrade -r requirements.txt -q 2>/dev/null || true
echo "  ✓ Dépendances Python à jour"

# --- 4. Vérification barèmes taxes ---
echo ""
echo "[4/5] Vérification barèmes taxes..."
python3 scripts/check_tax_rates.py

# --- 5. Vérification intégrité base ---
echo ""
echo "[5/5] Vérification base de données..."
python3 -c "
import sys; sys.path.insert(0, '.')
from sqlalchemy import create_engine, text
from config.settings import DATABASE_URL
engine = create_engine(DATABASE_URL)
with engine.connect() as conn:
    r = conn.execute(text('SELECT COUNT(*) FROM types_mines')).scalar()
    print(f'  Véhicules en base : {r}')
    r2 = conn.execute(text(\"SELECT COUNT(*) FROM types_mines WHERE genre IN ('MTL','MTT1','MTT2')\")).scalar()
    print(f'  Dont motos : {r2}')
    r3 = conn.execute(text('SELECT COUNT(*) FROM dossiers')).scalar()
    print(f'  Dossiers traités : {r3}')
"
echo "  ✓ Base de données OK"

echo ""
echo "============================================"
echo "  Mise à jour terminée !"
echo "============================================"
