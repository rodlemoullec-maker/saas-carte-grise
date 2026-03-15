# Vision Globale du Système

## Objectif

Automatiser le traitement des demandes de carte grise (certificat d'immatriculation)
dans le cadre de la vente de véhicules (motos, voitures, remorques).

Le système transforme un processus manuel de 15-20 min/dossier en un traitement
**entièrement autonome** avec validation humaine rapide uniquement.


## Rôle d'OpenClaw

**OpenClaw** est le cerveau central du système. C'est un agent IA autonome open source
qui orchestre l'intégralité du flux de traitement.

```
┌─────────────────────────────────────────────────────────────────────┐
│                        OPENCLAW (ORCHESTRATEUR)                     │
│                                                                     │
│  OpenClaw est un agent IA autonome qui :                            │
│  - Tourne en local sur le Mac Mini (zéro cloud)                    │
│  - Se connecte à Ollama pour utiliser les LLM locaux               │
│  - Reçoit les emails et déclenche le traitement                    │
│  - Exécute les skills (plugins) personnalisés                      │
│  - Gère le workflow de bout en bout                                │
│  - Prend des décisions autonomes (relancer le client si docs       │
│    manquants, alerter l'opérateur si incohérence, etc.)            │
│                                                                     │
│  L'opérateur n'intervient que pour la validation finale.           │
└─────────────────────────────────────────────────────────────────────┘
```


## Architecture avec OpenClaw

```
┌─────────────────────────────────────────────────────────────────────┐
│                         MAC MINI M4 16GB                            │
│                                                                     │
│  ┌───────────────────────────────────────────────────────────────┐  │
│  │                     OPENCLAW GATEWAY                          │  │
│  │              (agent autonome — cerveau central)               │  │
│  │                                                               │  │
│  │  Connecté à :                                                 │  │
│  │  ├── Ollama (LLM locaux : Qwen2.5-VL, Qwen2.5)             │  │
│  │  ├── Email (IMAP — canal d'entrée)                           │  │
│  │  └── Dashboard (Streamlit — canal opérateur)                 │  │
│  │                                                               │  │
│  │  Skills personnalisés (plugins Python) :                      │  │
│  │  ├── skill-classify    → classification documents             │  │
│  │  ├── skill-ocr         → OCR Surya + extraction données      │  │
│  │  ├── skill-vehicle     → recherche véhicule BDD              │  │
│  │  ├── skill-taxes       → calcul taxes carte grise            │  │
│  │  ├── skill-cerfa       → pré-remplissage PDF CERFA           │  │
│  │  ├── skill-validate    → cross-validation documents          │  │
│  │  └── skill-notify      → notifications client/opérateur      │  │
│  │                                                               │  │
│  └───────────────────────────────────────────────────────────────┘  │
│                              │                                      │
│              ┌───────────────┼───────────────┐                      │
│              ▼               ▼               ▼                      │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────┐            │
│  │   OLLAMA    │  │ POSTGRESQL  │  │  SYSTÈME FICHIERS│            │
│  │             │  │             │  │                   │            │
│  │ qwen2.5-vl │  │ types_mines │  │ data/dossiers/    │            │
│  │ qwen2.5    │  │ dossiers    │  │ data/output/      │            │
│  │             │  │ documents   │  │ templates/        │            │
│  │             │  │ stock       │  │                   │            │
│  └─────────────┘  └─────────────┘  └─────────────────┘            │
└─────────────────────────────────────────────────────────────────────┘
```


## Flux de traitement complet (piloté par OpenClaw)

```
┌─────────────────────────────────────────────────────────────────────┐
│                                                                     │
│  ÉTAPE 1 — RÉCEPTION (OpenClaw détecte l'email)                    │
│  La personne habilitée SIV envoie les pièces du client par email   │
│  → OpenClaw reçoit via canal IMAP                                  │
│  → Crée un dossier, sauvegarde les PJ                              │
│  → Envoie un accusé réception automatique                          │
│                           │                                         │
│                           ▼                                         │
│  ÉTAPE 2 — CLASSIFICATION (OpenClaw → skill-classify)              │
│  OpenClaw envoie chaque image au LLM vision (Qwen2.5-VL)          │
│  → Identifie : carte_grise, cni, cession, justificatif, CT        │
│  → Si document manquant → relance auto la personne habilitée       │
│                           │                                         │
│                           ▼                                         │
│  ÉTAPE 3 — OCR + EXTRACTION (OpenClaw → skill-ocr)                │
│  → Preprocessing image (OpenCV)                                    │
│  → Surya OCR → texte brut                                         │
│  → LLM texte (Qwen2.5) → JSON structuré par document              │
│                           │                                         │
│                           ▼                                         │
│  ÉTAPE 4 — RECHERCHE VÉHICULE (OpenClaw → skill-vehicle)          │
│  → Recherche BDD types mines (CNIT → specs techniques)            │
│  → Recherche base stock interne                                   │
│  → Décodage VIN                                                    │
│  → Fiche technique complète du véhicule                            │
│                           │                                         │
│                           ▼                                         │
│  ÉTAPE 5 — CROSS-VALIDATION (OpenClaw → skill-validate)           │
│  → VIN cohérent entre documents ?                                  │
│  → Nom CNI = nom acheteur ?                                       │
│  → Justificatif < 6 mois ?                                        │
│  → CNI non expirée ?                                               │
│  → Si erreur → OpenClaw alerte l'opérateur automatiquement         │
│                           │                                         │
│                           ▼                                         │
│  ÉTAPE 6 — CALCUL TAXES (OpenClaw → skill-taxes)                  │
│  → Y1 : taxe régionale (CV × tarif région)                        │
│  → Y3 : taxe formation professionnelle                             │
│  → Y4 : malus CO2       Y5 : malus masse                          │
│  → Y6 : taxe fixe (11€)                                           │
│                           │                                         │
│                           ▼                                         │
│  ÉTAPE 7 — CERFA (OpenClaw → skill-cerfa)                         │
│  → Pré-remplissage automatique CERFA 13750                         │
│  → PDF généré dans data/output/                                    │
│                           │                                         │
│                           ▼                                         │
│  ÉTAPE 8 — NOTIFICATION (OpenClaw → skill-notify)                  │
│  → Notifie l'opérateur : "Dossier CG-2026-0042 prêt à valider"   │
│  → Dashboard affiche le dossier complet                            │
│                           │                                         │
│                           ▼                                         │
│  ÉTAPE 9 — VALIDATION OPÉRATEUR (Dashboard Streamlit)              │
│  → Documents originaux côte à côte avec données extraites         │
│  → Correction rapide si erreur IA                                  │
│  → Bouton "Valider et générer CERFA final"                        │
│                           │                                         │
│                           ▼                                         │
│  ÉTAPE 10 — ENVOI (OpenClaw → skill-notify)                        │
│  → Envoie le CERFA pré-rempli par email à la personne habilitée   │
│  → La personne habilitée soumet le CERFA à l'ANTS                 │
│  → Notre rôle d'intermédiaire est terminé                         │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```


## Ce qu'OpenClaw apporte vs scripts Python seuls

| Aspect | Sans OpenClaw | Avec OpenClaw |
|---|---|---|
| Déclenchement | Script cron / polling manuel | Agent autonome, toujours actif |
| Décisions | Code if/else rigide | IA qui raisonne et s'adapte |
| Relance personne habilitée | Manuelle | Automatique (doc manquant détecté) |
| Gestion erreurs | Crash ou log | OpenClaw décide quoi faire |
| Extensibilité | Modifier le code | Ajouter un skill/plugin |
| Monitoring | Logs fichier | Interface OpenClaw + dashboard |
| Communication | Email uniquement | Email + WhatsApp + Slack (canaux OpenClaw) |


## Cas particuliers gérés

| Type véhicule | Spécificités |
|---|---|
| Voiture (VP) | CT obligatoire si > 4 ans, malus CO2, malus masse |
| Moto < 125cc (MTL) | Pas de CT, pas de malus CO2 |
| Moto > 125cc (MTT1/MTT2) | CT obligatoire depuis 2024, catégorie A1/A2/A |
| Remorque (REM/RESP) | PTAC/PTRA critiques, pas de puissance fiscale classique |


## Volumétrie cible

- Capacité : jusqu'à 200 dossiers/mois
- Temps de traitement IA : ~30 secondes par dossier (entièrement autonome)
- Temps validation humaine : ~2-3 minutes par dossier (seule intervention)
