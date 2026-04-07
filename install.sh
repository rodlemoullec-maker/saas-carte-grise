#!/usr/bin/env bash
#
# AutoDoc Pro — Script d'installation Linux/macOS
#
# Usage :
#     bash install.sh
#
# Ce script vérifie la présence de Docker, télécharge les fichiers nécessaires
# (s'ils ne sont pas déjà là), et lance le logiciel.
#
set -euo pipefail

# ─── Couleurs pour l'affichage ─────────────────────────────────────────────
RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

print_header() {
    echo
    echo -e "${BLUE}═══════════════════════════════════════════════════════════════${NC}"
    echo -e "${BLUE}  AutoDoc Pro — Installation${NC}"
    echo -e "${BLUE}═══════════════════════════════════════════════════════════════${NC}"
    echo
}

print_step() {
    echo -e "${BLUE}▸${NC} $1"
}

print_success() {
    echo -e "${GREEN}✓${NC} $1"
}

print_error() {
    echo -e "${RED}✗${NC} $1" >&2
}

print_warning() {
    echo -e "${YELLOW}⚠${NC} $1"
}

# ─── Vérifications préalables ──────────────────────────────────────────────

check_docker() {
    print_step "Vérification de Docker..."
    if ! command -v docker &> /dev/null; then
        print_error "Docker n'est pas installé."
        echo
        echo "Téléchargez Docker Desktop ici :"
        echo "  https://www.docker.com/products/docker-desktop/"
        exit 1
    fi
    if ! docker info &> /dev/null; then
        print_error "Docker est installé mais ne semble pas démarré."
        echo
        echo "Lancez Docker Desktop puis relancez ce script."
        exit 1
    fi
    print_success "Docker est installé et démarré"
}

check_compose() {
    print_step "Vérification de Docker Compose..."
    if ! docker compose version &> /dev/null; then
        print_error "Docker Compose v2 n'est pas disponible."
        echo
        echo "Mettez à jour Docker Desktop vers la dernière version."
        exit 1
    fi
    print_success "Docker Compose est disponible"
}

check_files() {
    print_step "Vérification des fichiers nécessaires..."
    local missing=()
    for f in Dockerfile docker-compose.yml requirements.txt; do
        if [[ ! -f "$f" ]]; then
            missing+=("$f")
        fi
    done
    if (( ${#missing[@]} > 0 )); then
        print_error "Fichiers manquants : ${missing[*]}"
        echo
        echo "Téléchargez l'archive complète d'AutoDoc Pro depuis :"
        echo "  https://autodocpro.fr/telecharger"
        exit 1
    fi
    print_success "Tous les fichiers nécessaires sont présents"
}

# ─── Création du dossier data ──────────────────────────────────────────────

prepare_data_dir() {
    print_step "Préparation du dossier data/..."
    if [[ ! -d "data" ]]; then
        mkdir -p data
        print_success "Dossier data/ créé"
    else
        print_success "Dossier data/ déjà présent"
    fi
}

# ─── Build et démarrage ────────────────────────────────────────────────────

build_and_start() {
    print_step "Build de l'image Docker (peut prendre 5 à 15 minutes)..."
    echo
    docker compose build
    echo
    print_step "Démarrage du conteneur..."
    docker compose up -d
}

# ─── Attente du healthcheck ────────────────────────────────────────────────

wait_for_health() {
    print_step "Vérification du démarrage (peut prendre jusqu'à 60 secondes)..."
    local attempts=0
    local max_attempts=60
    while (( attempts < max_attempts )); do
        if curl -sf http://localhost:8001/health > /dev/null 2>&1; then
            print_success "AutoDoc Pro est démarré et opérationnel"
            return 0
        fi
        sleep 1
        ((attempts++))
        if (( attempts % 10 == 0 )); then
            echo "    ... $attempts s"
        fi
    done
    print_warning "Le healthcheck n'a pas répondu après ${max_attempts}s."
    print_warning "Vérifiez les logs : docker compose logs autodocpro"
    return 1
}

# ─── Message final ─────────────────────────────────────────────────────────

print_final_instructions() {
    echo
    echo -e "${GREEN}═══════════════════════════════════════════════════════════════${NC}"
    echo -e "${GREEN}  ✓ AutoDoc Pro est installé et démarré${NC}"
    echo -e "${GREEN}═══════════════════════════════════════════════════════════════${NC}"
    echo
    echo "  Ouvrez votre navigateur web et allez à :"
    echo
    echo -e "      ${BLUE}http://localhost:8001${NC}"
    echo
    echo "  Commandes utiles :"
    echo
    echo "    docker compose logs -f autodocpro    # voir les logs"
    echo "    docker compose stop                   # arrêter"
    echo "    docker compose start                  # redémarrer"
    echo "    docker compose down                   # arrêter et supprimer"
    echo
    echo "  Vos données sont stockées dans : ./data/"
    echo "  (à sauvegarder régulièrement sur disque externe ou cloud personnel)"
    echo
}

# ─── Main ──────────────────────────────────────────────────────────────────

main() {
    print_header
    check_docker
    check_compose
    check_files
    prepare_data_dir
    build_and_start
    wait_for_health || true
    print_final_instructions
}

main "$@"
