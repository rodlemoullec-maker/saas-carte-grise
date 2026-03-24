# Roadmap Produit

## Phase 1 — MVP (Neuf Pro→Particulier)

**Objectif** : premier cas d'usage complet, end-to-end, en production chez 5 garages pilotes.

| Module | Priorité | Description |
|--------|----------|-------------|
| Pipeline OCR + extraction | P0 | COC, Facture, CNI, Domicile, Permis, Assurance |
| Moteur de règles + scoring | P0 | Croisements VIN, identité, véhicule |
| API REST | P0 | Upload, décision, soumission SIV |
| Dashboard agent | P0 | Liste dossiers + file de revue |
| Notifications email | P0 | Pro + client |
| Intégration SIV ANTS | P0 | Vérification VIN + soumission |
| Auth JWT + RBAC | P0 | Admin, agent, commercial |
| Audit trail | P0 | Log horodaté de toutes les actions |

## Phase 2 — Occasion + Portail client

| Module | Description |
|--------|-------------|
| Cas occasion (pro→particulier) | CERFA 15776 + CG barée + contrôle technique |
| Cas cession particuliers | Déclaration cession + règles spécifiques |
| Portail client mobile | Page upload documents depuis téléphone |
| SMS notifications | Twilio ou OVH SMS |
| Analytics avancées | Métriques KPI dans le dashboard |

## Phase 3 — Scalabilité et intégrations

| Module | Description |
|--------|-------------|
| Multi-tenants | Isolation données par professionnel |
| Intégration DMS | API pour Irium, CarsDB, Epyx... |
| Changement adresse / duplicata | Cas simples automatisables à 100% |
| Détection fraude avancée | Modèle ML sur anomalies documentaires |
| Application mobile | iOS/Android pour agents terrain |

## Phase 4 — Intelligence et optimisation

| Module | Description |
|--------|-------------|
| Apprentissage continu | Fine-tuning extracteurs sur cas terrain |
| Pré-remplissage SIV | Anticipation champs depuis base véhicules |
| Score risque client | Scoring basé sur historique dossiers |
| Intégration FCA | Vérification assurance en temps réel |

---

## Décisions techniques à prendre avant le développement

| Décision | Options | Impact |
|----------|---------|--------|
| OCR provider | Google DocAI vs Azure Form Recognizer | Coût, précision, RGPD (données EU) |
| LLM extraction | Claude Sonnet vs GPT-4o | Coût, vitesse, précision FR |
| BDD | PostgreSQL (recommandé) vs MongoDB | Schéma structuré → PostgreSQL |
| Queue | Celery+Redis vs ARQ vs RQ | Maturité → Celery |
| Auth | JWT custom vs Auth0 vs Keycloak | Rapidité dev → JWT custom |
| Hosting | AWS vs GCP vs OVH (RGPD FR) | Conformité → OVH ou AWS eu-west |
