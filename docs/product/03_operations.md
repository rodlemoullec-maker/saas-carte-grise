# Opérations — Exploitation et Maintenance

## 1. Déploiement

### Infrastructure minimale (V1)

```
Production :
├── 1 serveur app (API + Worker) : 4 vCPU, 8 GB RAM
├── 1 PostgreSQL managed (ex: Supabase, RDS, OVH Managed DB)
├── 1 Redis managed (ex: Upstash, ElastiCache)
├── 1 bucket S3 (ou équivalent) pour les documents
└── 1 CDN pour le dashboard Streamlit (ou déploiement séparé)

Recommandation RGPD :
→ Héberger sur OVH (France) ou AWS eu-west-3 (Paris)
→ Données clients stockées en France uniquement
```

### Variables sensibles

Jamais en code — toujours via variables d'environnement :
- `APP_SECRET_KEY`, `JWT_SECRET`
- `ANTHROPIC_API_KEY`
- `SIV_API_KEY`, `SIV_HABILITATION_ID`
- `DATABASE_URL` (avec mot de passe)
- `AWS_SECRET_ACCESS_KEY`

## 2. Monitoring

### Métriques à surveiller

| Métrique | Seuil alerte | Action |
|---------|-------------|--------|
| Délai moyen pipeline | > 10 min | Vérifier Celery + OCR provider |
| Taux d'erreur API | > 1% | Vérifier logs Sentry |
| File Celery en attente | > 50 tâches | Scale worker |
| Taux d'échec OCR | > 5% | Vérifier provider OCR |
| Disponibilité SIV ANTS | < 99% | Alerte critique + file d'attente |
| Espace stockage documents | > 80% | Archivage ou extension |

### Outils recommandés

- **Sentry** : suivi des erreurs Python
- **Grafana + Prometheus** : métriques système
- **Flower** : monitoring Celery (UI)
- **Uptime Robot** : monitoring uptime API

## 3. RGPD et conformité

### Données personnelles traitées

| Donnée | Source | Rétention | Action RGPD |
|--------|--------|-----------|-------------|
| Nom, prénom | CNI / Permis / Assurance | Durée légale + 5 ans | Droit à l'oubli → purge |
| Date de naissance | CNI / Permis | Durée légale + 5 ans | Droit à l'oubli → purge |
| Adresse domicile | Justificatif | Durée légale + 5 ans | Droit à l'oubli → purge |
| Photos documents | Tous | 3 mois après clôture | Suppression automatique |
| VIN | COC / Facture | Durée légale | Non personnel |
| Données SIV soumises | Payload | Durée légale + 5 ans | Archive chiffrée |

### Obligations

- Registre des traitements (RGPD art. 30)
- DPO désigné si volume > seuil
- Chiffrement au repos et en transit
- Journalisation des accès aux données personnelles
- Procédure de réponse aux droits (accès, effacement, portabilité)

## 4. Sécurité opérationnelle

### Checklist déploiement

- [ ] Secrets en variables d'environnement (jamais en code ou `.env` committé)
- [ ] TLS 1.3 uniquement (certificat Let's Encrypt ou ACM)
- [ ] Base de données non exposée publiquement (VPC privé)
- [ ] Sauvegardes BDD quotidiennes avec test de restauration mensuel
- [ ] Rate limiting API activé
- [ ] Headers sécurité HTTP (HSTS, CSP, X-Frame-Options)
- [ ] Logs centralisés (sans données sensibles en clair)
- [ ] Processus de rotation des clés API (tous les 90 jours)
- [ ] Plan de réponse incident documenté

### Accès et permissions

| Rôle | Accès |
|------|-------|
| `admin_saas` | Tout (gestion comptes, config globale) |
| `agent_habilite` | Dossiers de son organisation, revue, soumission SIV |
| `commercial` | Créer dossiers, uploader documents (pas de décision ni soumission SIV) |
| `api_client` | Endpoints API selon scope OAuth2 |

## 5. Support et incidents

### Niveaux de support (V1)

| Niveau | Délai de réponse | Canal |
|--------|-----------------|-------|
| P0 — SIV indisponible | 30 min | Téléphone + email |
| P1 — Pipeline bloqué | 2h | Email |
| P2 — Bug fonctionnel | 24h | Ticket support |
| P3 — Question usage | 48h | Documentation + email |

### Procédure rejet SIV inattendu

1. Capturer le code erreur SIV + payload envoyé (sans données sensibles)
2. Vérifier le log du dossier côté SaaS
3. Si erreur technique SIV → réessai automatique (3 fois max, backoff 10 min)
4. Si erreur métier → retourner en CORRECTION avec message explicite
5. Si erreur inconnue → escalade agent habilité + support technique
