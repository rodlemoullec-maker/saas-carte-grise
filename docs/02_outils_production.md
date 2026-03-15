# Outils utilisés en production (traitement opérationnel)

Ce document liste les outils et technologies qui feront tourner le service
une fois le développement terminé.


## OpenClaw — Orchestrateur IA autonome

| Propriété | Détail |
|---|---|
| **Rôle** | Cerveau central — orchestre tout le flux automatiquement |
| **Type** | Agent IA autonome open source |
| **Licence** | MIT |
| **Créateur** | Peter Steinberger (ex-PSPDFKit) |
| **GitHub** | 280k+ stars — projet open source le plus populaire |
| **Prérequis** | Node.js 22+ |

**Ce que fait OpenClaw dans notre système :**
- Se connecte à Ollama pour utiliser les LLM locaux (qwen2.5-vl, qwen2.5)
- Reçoit les emails clients via canal IMAP
- Déclenche automatiquement le workflow de traitement
- Exécute les skills personnalisés (classification, OCR, extraction, etc.)
- Prend des décisions autonomes (relancer un client, alerter l'opérateur)
- Gère les erreurs intelligemment (pas de crash, il raisonne)
- Supporte plusieurs canaux : email, WhatsApp, Slack, Discord

**Installation :**
```bash
# Installer OpenClaw
npm install -g openclaw

# Setup guidé (configure Ollama, daemon, etc.)
openclaw onboard --install-daemon
```

**Configuration Ollama dans OpenClaw (~/.openclaw/openclaw.json) :**
```json
{
  "provider": {
    "type": "ollama",
    "api": "openai-completions",
    "url": "http://127.0.0.1:11434/v1",
    "model": "qwen2.5:7b"
  }
}
```

**Important :** Utiliser un contexte d'au moins 64k tokens pour les modèles locaux.
Le system prompt, les skills, la mémoire et l'historique partagent la même fenêtre.


## Skills OpenClaw (plugins personnalisés)

Chaque module métier devient un "skill" OpenClaw — un plugin que l'agent
peut appeler de manière autonome quand il en a besoin.

| Skill | Rôle | Technologie sous-jacente |
|---|---|---|
| `skill-classify` | Classifier un document (image → type) | Qwen2.5-VL via Ollama |
| `skill-ocr` | Extraire le texte d'un document | Surya OCR + OpenCV |
| `skill-extract` | Structurer le texte OCR en JSON | Qwen2.5 via Ollama |
| `skill-vehicle` | Rechercher un véhicule en BDD | PostgreSQL (types mines + stock) |
| `skill-taxes` | Calculer les taxes carte grise | Barèmes régionaux locaux |
| `skill-cerfa` | Pré-remplir le CERFA 13750 | fillpdf + pdfrw |
| `skill-validate` | Cross-valider les documents | Logique métier Python |
| `skill-notify` | Notifier client ou opérateur | Email SMTP / canal OpenClaw |

Les skills sont écrits en Python et exposés à OpenClaw via son Plugin SDK.


## IA locale (via Ollama)

| Modèle | Rôle | RAM | Licence |
|---|---|---|---|
| **Qwen2.5-VL:7b** | Classification documents (vision) | ~6 GB | Apache 2.0 |
| **Qwen2.5:7b** | Extraction structurée texte OCR → JSON | ~5 GB | Apache 2.0 |
| Mistral-Small:22b | Fallback si extraction complexe (optionnel) | ~14 GB | Apache 2.0 |

**Installation :**
```bash
ollama pull qwen2.5vl:7b
ollama pull qwen2.5:7b
```


## OCR

| Outil | Rôle | Qualité FR | Vitesse (Apple Silicon) |
|---|---|---|---|
| **Surya** | OCR principal — extraction texte depuis scans/photos | Excellent | ~2-5s/page (MPS) |
| DocTR | Fallback rapide si Surya échoue | Très bon | ~1-3s/page |

**Installation :**
```bash
pip install surya-ocr
```

**Licence :** GPL 3.0 (usage interne OK, pas de redistribution)


## Prétraitement image

| Outil | Rôle |
|---|---|
| **OpenCV** | Redressement perspective, contraste, débruitage |

Appliqué automatiquement avant OCR pour les photos smartphone (qualité variable).


## Base de données

| Composant | Technologie | Contenu |
|---|---|---|
| **BDD principale** | PostgreSQL | Dossiers, documents, véhicules stock |
| **Base types mines** | Table PostgreSQL | ~500k entrées (CNIT → caractéristiques techniques) |
| **Source types mines** | data.gouv.fr | CSV officiel, gratuit |


## Génération PDF

| Outil | Rôle |
|---|---|
| **fillpdf** | Remplissage des champs AcroForm du CERFA officiel |
| **pdfrw** | Manipulation bas niveau PDF si nécessaire |
| **reportlab** | Génération contenu PDF complémentaire |


## Interface opérateur

| Outil | Rôle |
|---|---|
| **Streamlit** | Dashboard web — validation dossiers par l'opérateur |

L'opérateur n'intervient que pour la validation finale.
OpenClaw gère tout le reste de manière autonome.


## Stack complète

```
┌─────────────────────────────────────────────────┐
│              COUCHE ORCHESTRATION                │
│  OpenClaw Gateway (agent autonome)              │
│  → pilote tout, prend les décisions             │
├─────────────────────────────────────────────────┤
│              COUCHE IA                           │
│  Ollama (Qwen2.5-VL + Qwen2.5)                 │
│  Surya OCR + OpenCV                             │
│  → classification, OCR, extraction              │
├─────────────────────────────────────────────────┤
│              COUCHE MÉTIER                       │
│  Skills Python (plugins OpenClaw)               │
│  → recherche véhicule, taxes, CERFA, validation│
├─────────────────────────────────────────────────┤
│              COUCHE DONNÉES                      │
│  PostgreSQL (types mines, dossiers, stock)       │
│  Système fichiers (documents, PDF générés)      │
├─────────────────────────────────────────────────┤
│              COUCHE INTERFACE                    │
│  Streamlit (dashboard opérateur)                │
│  Email IMAP/SMTP (communication client)         │
│  WhatsApp/Slack (optionnel via OpenClaw)         │
└─────────────────────────────────────────────────┘
```


## Coût opérationnel mensuel

| Poste | Coût |
|---|---|
| OpenClaw | 0 € (open source, local) |
| IA (Ollama, Surya) | 0 € (local) |
| PostgreSQL | 0 € (local) |
| Licences | 0 € (tout open source) |
| Hébergement | 0 € (Mac Mini sur site) |
| **Total** | **0 €** (hors électricité) |
