# SaaS Carte Grise — Moteur d'Automatisation

Système d'automatisation du traitement des demandes de carte grise (certificats d'immatriculation) destiné aux professionnels de l'automobile (garages, concessions, revendeurs).

## Cas d'usage couverts

| Type | Description | Statut |
|------|-------------|--------|
| `NEUF_PRO_PARTICULIER` | Vente véhicule neuf, professionnel → particulier | En cours |
| `OCCASION_PRO_PARTICULIER` | Vente véhicule occasion, professionnel → particulier | A venir |
| `OCCASION_PARTICULIER_PARTICULIER` | Cession entre particuliers | A venir |
| `CHANGEMENT_ADRESSE` | Mise à jour domicile titulaire | A venir |
| `DUPLICATA` | Perte ou vol de carte grise | A venir |

## Architecture

```
engine/         → Moteur métier pur (OCR, validation, croisements, décision)
integrations/   → Connecteurs APIs externes (INSEE, BAN, NHTSA, ANTS/SIV)
api/            → API REST FastAPI (point d'entrée SaaS)
dashboard/      → Interface agent habilité (Streamlit)
workers/        → Tâches asynchrones (pipeline, notifications)
storage/        → Gestion fichiers documents
notifications/  → Email / SMS
config/         → Configuration centralisée
tests/          → Tests unitaires, intégration, e2e
docs/           → Spécifications métier et technique
```

## Installation

```bash
cp .env.example .env
# Remplir les variables dans .env

pip install -e ".[dev]"

# Avec Docker
docker-compose up -d
```

## Démarrage rapide

```bash
# API
uvicorn api.main:app --reload

# Dashboard agent
streamlit run dashboard/app.py

# Worker pipeline
celery -A workers.pipeline worker --loglevel=info
```

## Tests

```bash
pytest tests/unit/
pytest tests/integration/
pytest tests/e2e/
```

## Documentation

- [Vision produit](docs/specs/00_vision_produit.md)
- [Règles métier — Neuf](docs/specs/01_regles_metier_neuf.md)
- [Architecture globale](docs/architecture/01_architecture_globale.md)
- [Modèle de données](docs/architecture/02_modele_donnees.md)
