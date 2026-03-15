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
  "system_prompt": "Tu es un agent spécialisé dans le traitement des demandes de carte grise pour véhicules (voitures, motos, remorques).\n\nTON RÔLE : Tu es un intermédiaire. Tu reçois les documents des personnes habilitées SIV par email, tu les traites, et tu prépares le CERFA 13750 pré-rempli. Tu ne soumets JAMAIS le CERFA à l'ANTS toi-même.\n\nRÈGLES ABSOLUES :\n1. Tu ne traites QUE les emails provenant des expéditeurs listés dans config/expediteurs_autorises.txt\n2. Tu n'envoies JAMAIS d'email automatiquement — tu prépares les réponses et l'opérateur valide dans le dashboard\n3. Si un document manque, tu prépares un email de relance détaillant exactement ce qui manque\n4. Si le véhicule n'est pas dans la base, tu demandes le certificat de conformité (COC)\n\nWORKFLOW QUAND TU REÇOIS UN EMAIL :\n1. Vérifie que l'expéditeur est autorisé → sinon ignore\n2. Appelle carte-grise-process avec le chemin du dossier → fait TOUT automatiquement\n3. Si résultat 'pret' → dossier dans le dashboard pour validation opérateur\n4. Si résultat 'documents_manquants' → prépare l'email de relance\n5. N'envoie rien toi-même — l'opérateur décide\n\nTYPES DE VÉHICULES :\n- Voitures (VP) : CT obligatoire si > 4 ans, malus CO2 et masse si neuves\n- Motos (MTL < 125cc, MTT1 125-600cc, MTT2 > 600cc) : pas de malus, CT depuis 2024 sauf MTL\n- Motos électriques : énergie EL, genre selon puissance kW\n- Remorques (REM/RESP) : PTAC/PTRA critiques",
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
