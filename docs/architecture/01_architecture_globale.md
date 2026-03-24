# Architecture Globale

## Vue d'ensemble

```
┌─────────────────────────────────────────────────────────────────┐
│                        CLIENTS                                   │
│   Pro habilité (dashboard)  │  API consumer  │  Client (upload) │
└───────────┬─────────────────┴───────┬─────────┴─────────────────┘
            │                         │
┌───────────▼─────────────────────────▼─────────────────────────┐
│                         API FastAPI                             │
│   /dossiers  /documents  /decisions  /webhooks                  │
│   Auth JWT   Rate limiting   Audit log                          │
└───────────────────────────────┬─────────────────────────────────┘
                                │ (async via Redis queue)
┌───────────────────────────────▼─────────────────────────────────┐
│                     PIPELINE (Celery Worker)                     │
│                                                                  │
│  [INTAKE] → [EXTRACT] → [VALIDATE] → [CROSSCHECK] → [DECIDE]   │
│                                                                  │
│  ┌────────────┐  ┌──────────────┐  ┌──────────────────────────┐ │
│  │  OCR/LLM   │  │  Validators  │  │  Decision Engine         │ │
│  │  Extractors│  │  (VIN, SIRET │  │  (rules + scoring)       │ │
│  └────────────┘  │   dates...)  │  └──────────────────────────┘ │
│                  └──────────────┘                                │
└───────────────────────────────┬─────────────────────────────────┘
                                │
          ┌─────────────────────┼─────────────────────┐
          │                     │                     │
┌─────────▼──────┐   ┌─────────▼──────┐   ┌─────────▼──────┐
│  SIV / ANTS    │   │  Review Queue  │   │  Notifications  │
│  (soumission)  │   │  (agent)       │   │  (email/SMS)    │
└────────────────┘   └────────────────┘   └────────────────┘
```

## Modules

### `engine/` — Moteur métier pur

Aucune dépendance réseau, aucune dépendance BDD. Logique métier testable en isolation.

| Sous-module | Rôle |
|-------------|------|
| `models/` | Structures de données (Pydantic) : Dossier, Document, Decision |
| `extractors/` | OCR + extraction structurée par type de document |
| `validators/` | Validation individuelle de chaque champ |
| `cross_checks/` | Croisements et cohérence inter-documents |
| `decision/` | Moteur de règles + scoring + output décision |
| `normalizers/` | Normalisation noms, adresses, données véhicule |

### `integrations/` — Connecteurs externes

| Module | API cible | Usage |
|--------|-----------|-------|
| `insee_sirene.py` | api.insee.fr/sirene | Validation SIRET actif |
| `ban_addresses.py` | api-adresse.data.gouv.fr | Normalisation adresses |
| `nhtsa_vin.py` | vpic.nhtsa.dot.gov | Décodage WMI/VIN |
| `siv_ants.py` | API ANTS (SIV) | Vérification + soumission |
| `ocr_providers/` | Google Doc AI / Azure | OCR documents |

### `api/` — API REST

FastAPI. Points d'entrée pour les clients SaaS.

| Router | Endpoints |
|--------|-----------|
| `dossiers` | CRUD dossiers, upload documents |
| `documents` | Upload, re-upload, statut extraction |
| `decisions` | Résultat décision, override agent |
| `webhooks` | Callbacks SIV, notifications entrantes |

### `dashboard/` — Interface agent habilité

Streamlit. Accès restreint aux agents habilités.

| Page | Contenu |
|------|---------|
| `01_dossiers` | Liste tous les dossiers, filtres, recherche |
| `02_review_queue` | File d'attente des dossiers à valider manuellement |
| `03_analytics` | Métriques : taux acceptation, rejets, délais |
| `04_settings` | Config comptes, préférences |

### `workers/` — Tâches asynchrones

Celery + Redis. Le pipeline de traitement est entièrement asynchrone.

| Worker | Tâches |
|--------|--------|
| `pipeline` | Orchestration extraction → validation → décision → soumission |
| `notifications` | Envoi emails/SMS lors des changements de statut |

## Flux de données — Dossier neuf

```
1. Client/Pro upload documents via API
   → Fichiers stockés en storage (S3/local)
   → Dossier créé en BDD avec statut PENDING

2. Worker pipeline déclenché (async)
   → OCR + extraction par doc type
   → Normalisation des données extraites
   → Validation individuelle chaque document
   → Croisements inter-documents
   → Calcul du score
   → Application des règles bloquantes

3a. Score ≥ 95, 0 règle bloquante
   → Statut : ACCEPTE
   → Préparation payload SIV
   → Soumission ANTS
   → Notification Pro + Client

3b. Score 60–94 ou warnings
   → Statut : REVUE_AGENT
   → Apparition dans Review Queue dashboard
   → Agent valide ou demande corrections
   → Si validé : soumission SIV

3c. Règle bloquante ou score < 60
   → Statut : REJET ou CORRECTION
   → Message d'erreur détaillé
   → Notification Pro avec actions requises
```

## Sécurité

| Mesure | Implémentation |
|--------|---------------|
| Auth API | JWT (access + refresh tokens) |
| Autorisations | RBAC (admin, agent habilité, commercial) |
| Chiffrement transit | TLS 1.3 |
| Chiffrement repos | AES-256 (S3 SSE ou équivalent) |
| Rate limiting | Par IP + par compte |
| Audit trail | Log horodaté de chaque action sur dossier |
| RGPD | Purge automatique des documents après délai légal |
| Secrets | Variables d'environnement, jamais en code |
