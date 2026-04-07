# Audit complet — AutoDoc Pro — 4 avril 2026

## 1. SERVICES EXTERNES — État, coûts, limites

### 1.1 Anthropic (Claude Opus 4)

| Élément | État | Détail |
|---|---|---|
| Clé API | ✅ Configurée | Dans `.env` (`ANTHROPIC_API_KEY`) |
| Modèle utilisé | `claude-opus-4-20250514` | Le plus puissant — extraction + classification + vérification |
| Fonctions | `claude_classify()`, `claude_extract()`, `claude_verify()` | 3 appels par document uploadé |
| RGPD | ✅ Conforme | Données non conservées par Anthropic (API, pas d'entraînement) |
| Coût estimé | ~0.15-0.50€ par document | Prompt ~2K tokens input + ~500 tokens output × 3 appels |
| Coût par dossier | ~1-3€ (5-6 documents par dossier) | Sur un pricing de 12-14€ → marge OK |
| Limite API | 4000 req/min (tier payant) | Pas un problème au lancement |
| Risque | Coût variable selon la longueur OCR | Les COC européens longs coûtent plus cher |
| TODO | Rien — fonctionnel | Peut-être passer à Sonnet pour réduire les coûts (moins cher, suffisant pour l'extraction) |

### 1.2 Google Document AI (OCR)

| Élément | État | Détail |
|---|---|---|
| Credentials | ✅ Fichier JSON présent | `gen-lang-client-0123501972-a55d0eeea7d2.json` |
| Project | `275852582765` | Configuré dans `.env` |
| Processor | `6a6fede4a9a9caf1` | Région EU |
| Coût | ~0.01-0.05€ par page | 1000 pages/mois gratuites, puis $1.50/1000 pages |
| Coût par dossier | ~0.05-0.30€ (5-6 documents) | Négligeable |
| Limite gratuite | 1000 pages/mois | Suffisant pour ~150-200 dossiers/mois |
| Risque | Quota dépassé → erreur 429 | Prévoir fallback ou alerte |
| TODO | Rien — fonctionnel | |

### 1.3 Neon (PostgreSQL)

| Élément | État | Détail |
|---|---|---|
| URL | ✅ Configurée | `ep-weathered-base-al4nwrz1-pooler.c-3.eu-central-1.aws.neon.tech/neondb` |
| Région | Francfort (UE) | Conforme RGPD |
| Plan | Free tier | 512 MB storage, 0.25 compute units |
| Limite | 3 GB de données transférées/mois | Suffisant au lancement |
| Risque | Le free tier se met en veille après 5 min d'inactivité | Premier appel lent (~2-3 sec cold start) |
| TODO | Migrer vers plan payant ($19/mois) quand le volume augmente |

### 1.4 AWS S3 (Stockage documents)

| Élément | État | Détail |
|---|---|---|
| Bucket | `carte-grise-documents-saas` | Région eu-west-3 (Paris) |
| Configuré | ⚠️ Partiellement | `STORAGE_BACKEND=local` dans `.env` — S3 pas activé |
| Coût | ~$0.023/GB/mois | Négligeable pour des documents |
| TODO | Passer `STORAGE_BACKEND=s3` en production | Les documents sont stockés en local pour le dev |

### 1.5 Twilio / OVH SMS — NON CONFIGURÉ

| Élément | État | Détail |
|---|---|---|
| Intégration | ❌ Stub | `send_sms()` log uniquement |
| Clé API | ❌ Manquante | Pas dans `.env` ni dans `settings.py` |
| Coût Twilio | ~0.07€/SMS (France) | ~0.35€ par dossier (5 SMS : lien + rappels) |
| Coût OVH SMS | ~0.05€/SMS | Moins cher, API plus simple |
| TODO | Créer un compte Twilio/OVH, obtenir clés, implémenter `send_sms()` |

### 1.6 Stripe — NON CONFIGURÉ

| Élément | État | Détail |
|---|---|---|
| Intégration | ❌ Non implémentée | `engine/payment/honoraires.py` = docstring seulement |
| Clé API | ❌ Manquante | Pas dans `.env` |
| Champs BDD | ✅ Présents | `stripe_customer_id`, `payment_preauth_id`, `payment_captured`, `montant_honoraires` |
| Commission Stripe | 1.4% + 0.25€ par transaction | Sur 14€ → 0.45€ de commission → marge OK |
| TODO | Créer compte Stripe, implémenter checkout/pré-auth, webhooks paiement |

### 1.7 Redis (Celery) — NON CONFIGURÉ EN PRODUCTION

| Élément | État | Détail |
|---|---|---|
| Config | ✅ Dans settings.py | `redis://localhost:6379/0` |
| Installé localement | ❌ Pas vérifié | Celery ne tourne pas |
| Nécessaire pour | Workers asynchrones, rate limiting, cache | |
| TODO | Installer Redis en production (Railway addon ou Upstash gratuit) |

### 1.8 Formspree — NON CONFIGURÉ

| Élément | État | Détail |
|---|---|---|
| ID | ❌ Placeholder | `VOTRE_ID` dans les formulaires du site |
| Coût | Gratuit (50 soumissions/mois) | Suffisant au lancement |
| TODO | Créer compte Formspree, remplacer `VOTRE_ID` dans index.html, vendeur.html, agent.html |

### 1.9 Sentry (Monitoring) — NON CONFIGURÉ

| Élément | État | Détail |
|---|---|---|
| DSN | ❌ Vide | `sentry_dsn: str = ""` dans settings.py |
| Coût | Gratuit (5K events/mois) | Suffisant |
| TODO | Créer compte Sentry, ajouter DSN dans `.env` |

---

## 2. FICHIERS ET DONNÉES PRÉSENTS

### 2.1 Templates Cerfa PDF

| Fichier | Présent | Taille |
|---|---|---|
| `data/cerfa_templates/cerfa_13749.pdf` (VN) | ✅ Oui | 565 Ko |
| `data/cerfa_templates/cerfa_13750.pdf` (VO) | ✅ Oui | 539 Ko |
| `data/cerfa_templates/cerfa_15776.pdf` (Cession) | ❌ Manquant | — |
| `data/cerfa_templates/cerfa_13757.pdf` (Mandat) | ❌ Manquant | — |

### 2.2 Credentials fichiers

| Fichier | Présent | Sécurité |
|---|---|---|
| `.env` | ✅ 19 variables | ⚠️ Vérifier qu'il est dans `.gitignore` |
| `gen-lang-client-*.json` (GCP) | ✅ Présent | ⚠️ Ne doit PAS être committé |

### 2.3 Documents de test

| Dossier | Contenu |
|---|---|
| `data/documents/11111111-.../` | Documents du dossier de test |
| `data/documents/006174ad-.../` | Documents d'un autre dossier |

### 2.4 Docker

| Fichier | Présent | État |
|---|---|---|
| `Dockerfile` | ❌ Non trouvé | Référencé dans docker-compose mais absent |
| `docker-compose.yml` | ✅ Présent | Configure API + DB + Redis |

---

## 3. CONFIGURATION PRODUCTION MANQUANTE

### 3.1 Variables `.env` à ajouter pour la production

```
# Actuellement manquantes
TWILIO_ACCOUNT_SID=
TWILIO_AUTH_TOKEN=
TWILIO_PHONE_NUMBER=
STRIPE_SECRET_KEY=
STRIPE_WEBHOOK_SECRET=
SENTRY_DSN=
JWT_SECRET_KEY=           # Actuellement "changeme"
APP_SECRET_KEY=           # Actuellement "changeme"
REDIS_URL=                # Pour production (Upstash/Railway)
STORAGE_BACKEND=s3        # Actuellement "local"
AWS_ACCESS_KEY_ID=
AWS_SECRET_ACCESS_KEY=
AWS_S3_BUCKET=
```

### 3.2 Sécurité à corriger

| Problème | Fichier | Ligne |
|---|---|---|
| `app_secret_key = "changeme"` | config/settings.py | 21 |
| `allow_origins=["*"]` | api/main.py | 24 |
| `PRO_ID` hardcodé | frontend/src/App.tsx | 17 |
| `API = 'http://localhost:8001'` | frontend/src/App.tsx | 16 |
| Pas de HTTPS forcé | — | — |
| Pas de CSP headers | — | — |

---

## 4. COÛT TOTAL ESTIMÉ PAR DOSSIER (PRODUCTION)

| Poste | Coût unitaire | Par dossier (~6 docs) |
|---|---|---|
| Google Document AI (OCR) | 0.01-0.05€/page | ~0.15€ |
| Anthropic Claude (extraction) | 0.15-0.50€/doc | ~2.00€ |
| Twilio SMS (5 SMS) | 0.07€/SMS | ~0.35€ |
| Neon PostgreSQL | ~0€ (free tier) | ~0€ |
| S3 stockage | ~0€ | ~0€ |
| Stripe commission | 1.4% + 0.25€ | ~0.45€ |
| **Total coût par dossier** | | **~3.00€** |
| **Prix facturé** | | **12-14€** |
| **Marge par dossier** | | **~9-11€ (~70%)** |

### 4.1 Coûts fixes mensuels

| Poste | Coût |
|---|---|
| Hostinger Premium (site) | 2.99€ |
| Neon PostgreSQL (free → $19 si volume) | 0-19€ |
| Railway/Render (backend) | 0-5€ |
| Anthropic API (minimum) | ~20€ |
| Twilio (minimum) | ~5€ |
| Domaine (.fr) | ~1€/mois (~12€/an) |
| **Total fixe mensuel** | **~30-50€** |
| **Breakeven** | **~4-5 dossiers/mois** |

---

## 5. DÉPENDANCES PYTHON — État

| Package | Requis | Installé | État |
|---|---|---|---|
| `anthropic>=0.28.0` | Oui | ✅ | Fonctionnel |
| `httpx>=0.27.0` | Oui | ✅ | Pour API SIRENE |
| `fastapi>=0.111.0` | Oui | ✅ | Framework API |
| `sqlalchemy>=2.0.0` | Oui | ✅ | ORM async |
| `asyncpg>=0.29.0` | Oui | ✅ | Driver PostgreSQL |
| `pydantic>=2.7.0` | Oui | ✅ | Validation |
| `pillow>=10.3.0` | Oui | ✅ | Traitement images |
| `pdf2image>=1.17.0` | Oui | ✅ | PDF → images pour OCR |
| `pytesseract>=0.3.10` | Non | ✅ (installé mais plus utilisé) | Retiré du pipeline |
| `celery[redis]>=5.4.0` | Oui | ✅ | Workers (non fonctionnel) |
| `redis>=5.0.0` | Oui | ✅ | Broker Celery |
| `python-jose>=3.3.0` | Oui | ✅ | JWT (non implémenté) |
| `stripe` | ❌ Manquant | ❌ | À installer |
| `twilio` | ❌ Manquant | ❌ | À installer |
| `sentry-sdk` | ❌ Manquant | ❌ | À installer |
| `pdfrw` ou `PyPDF2` | ❌ Manquant | ❌ | Pour remplir les Cerfa PDF |
| `qrcode` | ❌ Manquant (backend) | ❌ | Pour QR codes URL permanente |

---

## 6. DÉPLOIEMENT — Ce qui manque

### 6.1 Backend (Railway/Render)

| Élément | État |
|---|---|
| Dockerfile | ❌ Manquant (référencé dans docker-compose mais absent) |
| requirements.txt | ✅ Présent |
| Procfile | ❌ Manquant (nécessaire pour Railway/Render) |
| Variable `PORT` | ❌ Non géré (hardcodé 8001) |
| Health check | ✅ `/health` endpoint existe |

### 6.2 Frontend React (Railway/Render)

| Élément | État |
|---|---|
| Build | ✅ `npx vite build` fonctionne |
| URL API | ❌ Hardcodé `localhost:8001` — doit être une variable d'env |
| Déploiement statique | ✅ `dist/` peut être servi par n'importe quel serveur statique |

### 6.3 Site commercial (Hostinger)

| Élément | État |
|---|---|
| Fichiers uploadés | ✅ En ligne |
| SSL | ⚠️ À vérifier |
| Domaine | ❌ Sous-domaine temporaire |
| Formspree | ❌ ID placeholder |
| Nettoyage fichiers | ❌ Doublons à supprimer |

---

## 7. TESTS — État

| Type | État | Détail |
|---|---|---|
| Tests unitaires | ⚠️ Partiels | `tests/unit/test_pipeline.py` existe |
| Tests d'intégration | ❌ Aucun | Pas de test du flux complet |
| Tests E2E | ❌ Aucun | Pas de Cypress/Playwright |
| Tests de charge | ❌ Aucun | Pas de benchmark |
| CI/CD | ❌ Aucun | Pas de GitHub Actions |

---

## 8. ORDRE DE PRIORITÉ POUR LE LANCEMENT

### Phase 1 — MVP testable (1 semaine)

| # | Tâche | Effort | Bloquant |
|---|---|---|---|
| 1 | Formspree — remplacer VOTRE_ID | 5 min | Formulaire ne marche pas |
| 2 | Domaine — connecter autodocpro.fr sur Hostinger | 30 min | URL pas pro |
| 3 | SSL — activer HTTPS | 5 min | Sécurité navigateur |
| 4 | Twilio — intégrer envoi SMS réel | 2h | Client ne reçoit pas le lien |
| 5 | Cerfa PDF — générer vrai PDF avec pdfrw | 1-2 jours | Pro ne peut pas télécharger le Cerfa |
| 6 | Cerfa templates — ajouter 15776 (cession) + 13757 (mandat) | 1h | Télécharger depuis service-public.gouv.fr |
| 7 | Cachet + signature sur PDF | 4h | Cerfa sort sans cachet |

### Phase 2 — Sécurité + paiement (1 semaine)

| # | Tâche | Effort |
|---|---|---|
| 8 | JWT — implémenter auth | 4h |
| 9 | CORS — restreindre aux domaines autorisés | 30 min |
| 10 | URL API — variable d'env dans le frontend | 30 min |
| 11 | Stripe — intégrer paiement | 1 jour |
| 12 | Déployer backend sur Railway | 2h |
| 13 | Déployer frontend sur Railway/Vercel | 1h |

### Phase 3 — Production (1 semaine)

| # | Tâche | Effort |
|---|---|---|
| 14 | Dockerfile | 1h |
| 15 | Sentry monitoring | 30 min |
| 16 | Rate limiting Redis | 2h |
| 17 | S3 stockage production | 1h |
| 18 | Email notifications pro | 4h |
| 19 | Tests E2E | 1-2 jours |
| 20 | CI/CD GitHub Actions | 2h |

### Phase 4 — Plus tard

| # | Tâche |
|---|---|
| 21 | Signature numérique cession (OTP réel) |
| 22 | Génération mandats 13757 |
| 23 | Partage dossier vendeur → agent |
| 24 | Workers Celery asynchrones |
| 25 | SIV ANTS (quand habilitation obtenue) |
| 26 | Vidéos de démo |
| 27 | Preuve sociale (témoignages) |
