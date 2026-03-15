#!/bin/bash
# ============================================
# Configuration OpenClaw pour Carte Grise Auto
# Installe les skills et configure Ollama
# ============================================

set -e

PROJECT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
OPENCLAW_SKILLS_DIR="$HOME/.openclaw/skills"

echo "============================================"
echo "  Configuration OpenClaw"
echo "  Projet : $PROJECT_DIR"
echo "============================================"
echo ""

# 1. Vérifier OpenClaw
if ! command -v openclaw &> /dev/null; then
    echo "Installation d'OpenClaw..."
    mkdir -p ~/.npm-global
    npm config set prefix "$HOME/.npm-global"
    export PATH="$HOME/.npm-global/bin:$PATH"
    npm install -g openclaw
    echo 'export PATH="$HOME/.npm-global/bin:$PATH"' >> ~/.zshrc
    echo "✓ OpenClaw installé"
else
    echo "✓ OpenClaw déjà installé : $(openclaw --version)"
fi

# 2. Créer le répertoire skills
mkdir -p "$OPENCLAW_SKILLS_DIR"

# 3. Générer les SKILL.md avec les chemins corrects
echo "Génération des skills..."

for skill_dir in "$PROJECT_DIR/skills"/skill-*; do
    skill_name=$(basename "$skill_dir")
    target_dir="$OPENCLAW_SKILLS_DIR/$skill_name"
    mkdir -p "$target_dir"

    # Lire le template SKILL.md et remplacer PROJECT_DIR
    if [ -f "$skill_dir/SKILL.md" ]; then
        sed "s|\\\$PROJECT_DIR|$PROJECT_DIR|g" "$skill_dir/SKILL.md" > "$target_dir/SKILL.md"
        echo "  ✓ $skill_name"
    fi
done

# 4. Configurer Ollama comme provider
mkdir -p "$HOME/.openclaw"

# Détecter la RAM et choisir le modèle
RAM_GB=$(sysctl -n hw.memsize 2>/dev/null | awk '{print int($1/1073741824)}')
if [ "$RAM_GB" -ge 48 ]; then
    MODEL="qwen2.5:32b"
elif [ "$RAM_GB" -ge 24 ]; then
    MODEL="qwen2.5:14b"
else
    MODEL="qwen2.5:7b"
fi

echo ""
echo "RAM détectée : ${RAM_GB} GB → Modèle : $MODEL"

cat > "$HOME/.openclaw/openclaw.json" << JSONEOF
{
  "provider": {
    "type": "ollama",
    "api": "openai-completions",
    "url": "http://127.0.0.1:11434/v1",
    "model": "$MODEL"
  },
  "system_prompt": "Tu es un agent spécialisé dans le traitement automatique des demandes de carte grise. Tu reçois les documents par email de la personne habilitée SIV, tu les traites via tes skills (classification, OCR, extraction, recherche véhicule, calcul taxes, génération CERFA), et tu renvoies le CERFA pré-rempli par email. Tu agis en tant qu'intermédiaire : tu ne soumets jamais le CERFA à l'ANTS toi-même.",
  "context_length": 65536
}
JSONEOF

echo "✓ Configuration Ollama ($MODEL)"

echo ""
echo "============================================"
echo "  OpenClaw configuré !"
echo "============================================"
echo ""
echo "Skills installés dans : $OPENCLAW_SKILLS_DIR"
echo "Config : ~/.openclaw/openclaw.json"
echo ""
echo "Pour démarrer : openclaw start"
echo ""
