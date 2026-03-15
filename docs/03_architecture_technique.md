# Architecture Technique

## Schéma des composants

```
┌──────────────────────────────────────────────────────────────────┐
│                       MAC MINI M4 16GB                           │
│                                                                  │
│  ┌────────────────────────────────────────────────────────────┐  │
│  │                  OPENCLAW GATEWAY                          │  │
│  │            (agent autonome — cerveau central)              │  │
│  │                                                            │  │
│  │   ┌──────────────────────────────────────────────────┐     │  │
│  │   │              SKILLS (plugins)                     │     │  │
│  │   │                                                   │     │  │
│  │   │  skill-classify ──→ Ollama (Qwen2.5-VL vision)  │     │  │
│  │   │  skill-ocr ──────→ Surya OCR + OpenCV           │     │  │
│  │   │  skill-extract ──→ Ollama (Qwen2.5 texte)       │     │  │
│  │   │  skill-vehicle ──→ PostgreSQL                    │     │  │
│  │   │  skill-taxes ────→ Calcul local (barèmes)       │     │  │
│  │   │  skill-cerfa ────→ fillpdf (PDF)                │     │  │
│  │   │  skill-validate ─→ Logique métier               │     │  │
│  │   │  skill-notify ───→ Email SMTP / canaux          │     │  │
│  │   └──────────────────────────────────────────────────┘     │  │
│  │                                                            │  │
│  │   Canaux :                                                 │  │
│  │   ├── Email (IMAP) ← réception documents clients         │  │
│  │   ├── Dashboard (API) → interface opérateur               │  │
│  │   └── WhatsApp/Slack (optionnel) → notifications          │  │
│  └────────────────────────────────────────────────────────────┘  │
│                              │                                    │
│              ┌───────────────┼───────────────┐                    │
│              ▼               ▼               ▼                    │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────┐          │
│  │   OLLAMA    │  │ POSTGRESQL  │  │ SYSTÈME FICHIERS │          │
│  │ (port 11434)│  │ (port 5432) │  │                  │          │
│  │             │  │             │  │ data/dossiers/   │          │
│  │ qwen2.5-vl │  │ types_mines │  │ data/output/     │          │
│  │ qwen2.5    │  │ dossiers    │  │ templates/       │          │
│  │             │  │ documents   │  │                  │          │
│  │             │  │ stock       │  │                  │          │
│  └─────────────┘  └─────────────┘  └─────────────────┘          │
│                                                                  │
│  ┌────────────────────────────────────────────────────────────┐  │
│  │                  STREAMLIT (port 8501)                      │  │
│  │              Dashboard opérateur — validation              │  │
│  └────────────────────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────────────────────┘
```


## Flux de communication

```
Client (email)
      │
      ▼
OpenClaw Gateway ──── reçoit email via canal IMAP
      │
      ├──► skill-classify ──► Ollama (vision) ──► type document
      │
      ├──► skill-ocr ──► OpenCV + Surya ──► texte brut
      │
      ├──► skill-extract ──► Ollama (texte) ──► JSON structuré
      │
      ├──► skill-vehicle ──► PostgreSQL ──► fiche technique
      │
      ├──► skill-validate ──► cross-check ──► rapport erreurs
      │         │
      │         └──► si erreur → skill-notify → relance client
      │
      ├──► skill-taxes ──► calcul ──► montants Y1-Y6
      │
      ├──► skill-cerfa ──► fillpdf ──► CERFA PDF pré-rempli
      │
      └──► skill-notify ──► alerte opérateur "dossier prêt"
                                    │
                                    ▼
                          Dashboard Streamlit
                          (validation humaine)
                                    │
                                    ▼
                          CERFA final → impression / ANTS
```


## Structure des skills OpenClaw

Chaque skill est un module Python exposé à OpenClaw.

```
skills/
├── skill-classify/
│   ├── manifest.json          # Déclaration du skill (nom, description, params)
│   └── handler.py             # Logique : appel Ollama vision
│
├── skill-ocr/
│   ├── manifest.json
│   └── handler.py             # Logique : preprocessing + Surya
│
├── skill-extract/
│   ├── manifest.json
│   └── handler.py             # Logique : prompt LLM → JSON par type doc
│
├── skill-vehicle/
│   ├── manifest.json
│   └── handler.py             # Logique : requêtes PostgreSQL
│
├── skill-taxes/
│   ├── manifest.json
│   └── handler.py             # Logique : calcul barèmes
│
├── skill-cerfa/
│   ├── manifest.json
│   └── handler.py             # Logique : fillpdf
│
├── skill-validate/
│   ├── manifest.json
│   └── handler.py             # Logique : cross-check documents
│
└── skill-notify/
    ├── manifest.json
    └── handler.py             # Logique : envoi email/notification
```

Chaque `manifest.json` déclare :
- Le nom du skill
- Sa description (pour qu'OpenClaw sache quand l'utiliser)
- Les paramètres d'entrée/sortie
- Les dépendances


## Modèle de données (PostgreSQL)

### Table `dossiers`

| Colonne | Type | Description |
|---|---|---|
| id | SERIAL PK | Identifiant unique |
| reference | VARCHAR(20) | Référence interne (ex: CG-2026-0001) |
| email_source | VARCHAR(255) | Adresse email du client |
| client_nom | VARCHAR(200) | Nom complet du client |
| client_email | VARCHAR(255) | Email de contact |
| immatriculation | VARCHAR(15) | Immatriculation du véhicule |
| vin | VARCHAR(17) | Numéro VIN |
| type_operation | VARCHAR(50) | changement_titulaire, premiere_immat, duplicata... |
| region | VARCHAR(50) | Région pour calcul taxe |
| statut | VARCHAR(20) | nouveau, en_cours, documents_manquants, pret, valide, soumis |
| donnees_extraites | JSONB | Toutes les données extraites (fusion documents) |
| taxes | JSONB | Détail taxes calculées |
| cerfa_path | VARCHAR(500) | Chemin du CERFA généré |
| created_at | TIMESTAMP | Date de création |
| updated_at | TIMESTAMP | Dernière modification |

### Table `documents`

| Colonne | Type | Description |
|---|---|---|
| id | SERIAL PK | Identifiant unique |
| dossier_id | INT FK | Référence vers dossiers |
| type_document | VARCHAR(50) | carte_grise, cni, cession, justificatif... |
| fichier_path | VARCHAR(500) | Chemin du fichier sur disque |
| donnees_json | JSONB | Données extraites de ce document |
| confidence | FLOAT | Score de confiance classification (0-1) |
| ocr_texte_brut | TEXT | Texte brut OCR (pour debug/retraitement) |
| created_at | TIMESTAMP | Date d'import |

### Table `types_mines`

| Colonne | Type | Description |
|---|---|---|
| cnit | VARCHAR(20) PK | Code National d'Identification du Type |
| marque | VARCHAR(100) | Marque constructeur |
| denomination_commerciale | VARCHAR(200) | Nom commercial |
| genre | VARCHAR(10) | VP, MTL, MTT1, MTT2, CL, REM, RESP... |
| carrosserie | VARCHAR(50) | CI, BB, TS... |
| energie | VARCHAR(10) | ES, GO, EL, EH, GP... |
| cylindree | INTEGER | Cylindrée en cm³ |
| puissance_fiscale | INTEGER | Puissance administrative (CV) |
| puissance_kw | NUMERIC(6,2) | Puissance réelle en kW |
| co2 | INTEGER | Émissions CO2 (g/km) |
| nb_places | INTEGER | Places assises |
| poids_vide | INTEGER | Masse à vide (kg) |
| ptac | INTEGER | Poids total autorisé en charge (kg) |
| date_debut | DATE | Début de validité du type |
| date_fin | DATE | Fin de validité (NULL si actif) |

### Table `vehicules_stock`

| Colonne | Type | Description |
|---|---|---|
| id | SERIAL PK | Identifiant unique |
| vin | VARCHAR(17) UNIQUE | Numéro VIN |
| immatriculation | VARCHAR(15) | Immatriculation actuelle |
| cnit | VARCHAR(20) FK | Référence types_mines |
| marque | VARCHAR(100) | Marque |
| modele | VARCHAR(200) | Modèle |
| date_premiere_immat | DATE | Date 1ère immatriculation |
| km | INTEGER | Kilométrage |
| prix_vente | NUMERIC(10,2) | Prix de vente |
| statut | VARCHAR(20) | en_stock, vendu, reserve, en_cours_cg |
| date_entree | DATE | Date d'entrée en stock |
| date_vente | DATE | Date de vente |
