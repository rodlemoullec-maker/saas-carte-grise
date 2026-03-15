# WHITEPAPER
# Automatisation du traitement des demandes de carte grise
## Système intelligent pour professionnels de la vente automobile

---

**Version :** 1.0
**Date :** 15 mars 2026
**Projet :** Carte Grise Auto
**Cible :** Entreprises de vente de véhicules (voitures, motos, remorques)

---

## Table des matières

1. [Résumé exécutif](#1-résumé-exécutif)
2. [Contexte et problématique](#2-contexte-et-problématique)
3. [Solution proposée](#3-solution-proposée)
4. [Architecture du système](#4-architecture-du-système)
5. [Intelligence artificielle — Stratégie locale](#5-intelligence-artificielle--stratégie-locale)
6. [Modules fonctionnels](#6-modules-fonctionnels)
7. [OpenClaw — Orchestration autonome en production](#7-openclaw--orchestration-autonome-en-production)
8. [Modèle de données](#8-modèle-de-données)
9. [Sécurité et confidentialité](#9-sécurité-et-confidentialité)
10. [Plan de développement](#10-plan-de-développement)
11. [Analyse économique](#11-analyse-économique)
12. [Risques et mitigations](#12-risques-et-mitigations)
13. [Évolutions futures](#13-évolutions-futures)
14. [Conclusion](#14-conclusion)

---


## 1. Résumé exécutif

Ce document présente un système complet d'automatisation du traitement des
demandes de carte grise (certificat d'immatriculation) pour une entreprise
de vente de véhicules (voitures, motos, remorques) agissant en tant
qu'**intermédiaire** dans la chaîne de traitement.

**Le contexte métier :** L'entreprise reçoit les pièces administratives des
clients par l'intermédiaire d'une personne habilitée SIV. Elle traite le
dossier (vérification, extraction des données, pré-remplissage du CERFA),
puis renvoie le CERFA pré-rempli à la personne habilitée qui se charge
de la soumission auprès de l'administration (ANTS). L'entreprise n'effectue
pas elle-même la soumission.

**Le problème :** Chaque dossier nécessite la vérification et la saisie manuelle
de nombreux documents. Ce processus prend 15 à 20 minutes par dossier et est
source d'erreurs humaines.

**La solution :** Un système d'IA locale qui automatise l'intégralité du flux
intermédiaire : réception des documents par email depuis la personne habilitée,
classification automatique, extraction des données par OCR et IA, recherche
des caractéristiques techniques du véhicule, calcul des taxes, pré-remplissage
du CERFA 13750, et renvoi du CERFA complété par email à la personne habilitée.
L'opérateur n'intervient que pour une validation finale de 2 à 3 minutes.

**Le différenciateur :** Le système fonctionne entièrement en local, sans aucun
service cloud. L'intelligence artificielle tourne sur un Mac Mini M4 via Ollama,
les données restent sur site, et le coût opérationnel mensuel est de 0 euro
(hors électricité). En production, l'agent autonome OpenClaw orchestre
l'ensemble du flux sans intervention humaine.

**Résultat attendu :** Sur 200 dossiers par mois, le système économise environ
50 heures de travail administratif mensuel, élimine les erreurs de saisie,
et accélère le délai de traitement.


---


## 2. Contexte et problématique

### 2.1 Le marché

Les professionnels de la vente automobile (voitures, motos, remorques) traitent
quotidiennement des demandes de carte grise pour le compte de leurs clients.
Depuis la dématérialisation des démarches via l'ANTS (Agence Nationale des
Titres Sécurisés), les professionnels habilités SIV (Système d'Immatriculation
des Véhicules) peuvent effectuer directement ces démarches.

### 2.2 Le processus actuel

Pour chaque vente, l'opérateur doit :

1. **Réceptionner les documents** envoyés par la personne habilitée SIV :
   - Certificat d'immatriculation (carte grise) barré et signé
   - Certificat de cession (CERFA 15776) signé par vendeur et acheteur
   - Pièce d'identité de l'acheteur (CNI ou passeport)
   - Justificatif de domicile de moins de 6 mois
   - Contrôle technique de moins de 6 mois (si véhicule de plus de 4 ans)
   - Attestation d'assurance
   - Mandat/procuration (si applicable)

2. **Vérifier chaque document** :
   - Validité des pièces (dates, signatures)
   - Cohérence entre documents (VIN, noms, adresses)
   - Complétude du dossier

3. **Rechercher les informations techniques** du véhicule :
   - Code CNIT (Code National d'Identification du Type)
   - Genre national, énergie, cylindrée, puissance fiscale
   - Émissions CO2, PTAC, nombre de places

4. **Calculer les taxes** :
   - Taxe régionale (Y1)
   - Taxe de formation professionnelle (Y3)
   - Malus écologique CO2 (Y4)
   - Malus au poids (Y5)
   - Taxe fixe d'acheminement (Y6)

5. **Remplir manuellement** le CERFA 13750 (demande de certificat d'immatriculation) :
   - Environ 40 champs à saisir
   - Cases à cocher selon le type d'opération

6. **Renvoyer** le CERFA pré-rempli à la personne habilitée SIV
   (c'est elle qui soumet la demande sur le portail ANTS)

### 2.3 Les douleurs

| Problème | Impact |
|---|---|
| Saisie manuelle de ~40 champs par dossier | 15-20 min par dossier |
| Erreurs de transcription | CERFA renvoyé incorrect, délais supplémentaires |
| Vérification manuelle de cohérence | Risque d'oubli (VIN, dates, noms) |
| Recherche manuelle des caractéristiques techniques | Temps perdu sur bases de données |
| Documents reçus par email en vrac | Tri et classement chronophage |
| Relance manuelle de la personne habilitée pour documents manquants | Charge administrative |
| Calcul manuel des taxes | Erreurs possibles, barèmes complexes |

### 2.4 Spécificités métier

L'entreprise vend trois types de véhicules, chacun avec ses particularités
réglementaires :

**Voitures (genre VP) :**
- Contrôle technique obligatoire si véhicule de plus de 4 ans
- Malus CO2 applicable (barème annuel)
- Malus au poids applicable (> 1 800 kg)

**Motos :**
- Genre MTL (< 125 cm³), MTT1 (125-600 cm³), MTT2 (> 600 cm³)
- Contrôle technique obligatoire depuis 2024
- Pas de malus CO2
- Catégories permis A1/A2/A

**Remorques :**
- Genre REM (remorque) ou RESP (semi-remorque)
- PTAC et PTRA critiques pour la taxation
- Pas de puissance fiscale classique
- Pas de contrôle technique systématique


---


## 3. Solution proposée

### 3.1 Vision

Créer un système qui automatise **100% du traitement intermédiaire** d'une
demande de carte grise : de la réception de l'email de la personne habilitée
jusqu'au renvoi du CERFA pré-rempli par email, en ne laissant à l'opérateur
qu'une **validation de contrôle de 2 à 3 minutes**.

### 3.2 Principes fondateurs

| Principe | Justification |
|---|---|
| **100% local** | Aucune donnée ne quitte la machine. Pas de cloud, pas d'API payante. |
| **100% open source** | Zéro coût de licence. Indépendance vis-à-vis des fournisseurs. |
| **IA locale performante** | Modèles LLM tournant sur Apple Silicon via Ollama. |
| **Autonomie totale** | En production, l'agent OpenClaw gère tout sans intervention. |
| **Validation humaine** | L'opérateur garde le contrôle final sur chaque dossier. |
| **Modularité** | Chaque fonction est un module indépendant, testable, remplaçable. |

### 3.3 Flux cible

```
PERSONNE HABILITÉE SIV          SYSTÈME                         OPÉRATEUR
  │                                │                                │
  │  Envoie email avec les         │                                │
  │  pièces du client ────────────►│                                │
  │                                │                                │
  │  ◄──── Accusé réception ───────│                                │
  │         automatique            │                                │
  │                                │  Classification IA             │
  │                                │  OCR + Extraction              │
  │                                │  Recherche véhicule            │
  │                                │  Cross-validation              │
  │                                │  Calcul taxes                  │
  │                                │  Pré-remplissage CERFA         │
  │                                │                                │
  │                                │  ── Notification ─────────────►│
  │                                │     "Dossier prêt"             │
  │                                │                                │
  │                                │           Validation 2-3 min ──│
  │                                │  ◄── Valider ─────────────────│
  │                                │                                │
  │                                │  Génère CERFA PDF final        │
  │                                │                                │
  │  ◄──── CERFA pré-rempli ──────│                                │
  │        envoyé par email        │                                │
  │                                │                                │
  │  Soumet le CERFA               │                                │
  │  à l'ANTS ───────►  ANTS      │                                │
```

### 3.4 Deux phases distinctes

Le projet se décompose en deux phases clairement séparées :

**Phase de développement (Python classique) :**
- Chaque module est développé, testé et validé indépendamment
- Les modules sont appelés via des scripts Python ou l'API FastAPI
- L'IA (Ollama) est appelée directement depuis le code Python
- Le développeur (assisté par Claude) construit et teste chaque brique

**Phase opérationnelle (OpenClaw) :**
- Les modules Python sont encapsulés en "skills" OpenClaw
- OpenClaw devient le chef d'orchestre autonome
- Il surveille les emails, déclenche le traitement, prend des décisions
- L'opérateur n'utilise que le dashboard Streamlit pour valider


---


## 4. Architecture du système

### 4.1 Vue d'ensemble

```
┌──────────────────────────────────────────────────────────────────┐
│                       MAC MINI M4 16 GB                          │
│                                                                  │
│         DÉVELOPPEMENT                  PRODUCTION                │
│     ┌──────────────────┐          ┌──────────────────┐          │
│     │  Python / FastAPI │          │    OPENCLAW      │          │
│     │                  │          │  (agent autonome) │          │
│     │  Appels directs  │    ──►   │                  │          │
│     │  aux modules     │          │  Orchestre les   │          │
│     │  pour tests      │          │  skills (modules)│          │
│     └──────────────────┘          └──────────────────┘          │
│              │                             │                     │
│              └──────────┬──────────────────┘                     │
│                         ▼                                        │
│     ┌──────────────────────────────────────────────┐            │
│     │           MODULES PYTHON (src/)              │            │
│     │                                              │            │
│     │  classification/  → identifie le document    │            │
│     │  ocr/             → extrait le texte         │            │
│     │  extraction/      → structure en JSON        │            │
│     │  vehicle/         → recherche en BDD         │            │
│     │  taxes/           → calcule les taxes        │            │
│     │  cerfa/           → pré-remplit le PDF       │            │
│     │  validation/      → vérifie la cohérence     │            │
│     │  email_handler/   → gère les emails          │            │
│     │  pipeline/        → orchestre le flux         │            │
│     └──────────────────────────────────────────────┘            │
│                         │                                        │
│         ┌───────────────┼───────────────┐                        │
│         ▼               ▼               ▼                        │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────────┐           │
│  │   OLLAMA    │ │ POSTGRESQL  │ │ SYSTÈME FICHIERS │           │
│  │             │ │             │ │                   │           │
│  │ qwen2.5-vl │ │ types_mines │ │ data/dossiers/    │           │
│  │ qwen2.5    │ │ dossiers    │ │ data/output/      │           │
│  │             │ │ documents   │ │ templates/cerfa   │           │
│  │             │ │ stock       │ │                   │           │
│  └─────────────┘ └─────────────┘ └─────────────────┘           │
│                                                                  │
│  ┌────────────────────────────────────────────────────────────┐  │
│  │                  STREAMLIT (port 8501)                      │  │
│  │              Dashboard opérateur — validation              │  │
│  └────────────────────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────────────────────┘
```

### 4.2 Stack technologique

| Couche | Technologie | Rôle | Licence |
|---|---|---|---|
| **Orchestration (prod)** | OpenClaw | Agent autonome, pilote le flux | MIT |
| **Backend** | Python 3.14 + FastAPI | API REST, logique métier | MIT |
| **IA Vision** | Qwen2.5-VL:7b via Ollama | Classification documents | Apache 2.0 |
| **IA Texte** | Qwen2.5:7b via Ollama | Extraction structurée | Apache 2.0 |
| **OCR** | Surya | Reconnaissance de texte | GPL 3.0 |
| **Preprocessing** | OpenCV | Amélioration qualité image | Apache 2.0 |
| **BDD** | PostgreSQL | Données véhicules, dossiers | PostgreSQL |
| **PDF** | fillpdf + pdfrw + reportlab | Pré-remplissage CERFA | BSD |
| **Dashboard** | Streamlit | Interface opérateur | Apache 2.0 |
| **Email** | imaplib + smtplib (stdlib) | Réception/envoi emails | PSF |
| **Runtime IA** | Ollama | Serveur LLM local | MIT |

### 4.3 Configuration matérielle

| Composant | Spécification |
|---|---|
| Machine | Mac Mini M4 |
| RAM | 16 GB |
| Processeur | Apple M4 (CPU 10 cœurs, GPU 10 cœurs) |
| Neural Engine | 16 cœurs (accélération IA) |
| Stockage | SSD (256 GB minimum recommandé) |

**Utilisation RAM estimée en production :**

| Processus | RAM |
|---|---|
| Ollama + Qwen2.5-VL:7b (vision) | ~6 GB |
| Ollama + Qwen2.5:7b (texte) | ~5 GB |
| Surya OCR | ~2 GB |
| PostgreSQL | ~200 MB |
| OpenClaw Gateway | ~300 MB |
| Streamlit | ~200 MB |
| **Total en pic** | **~10 GB** |
| **Marge disponible** | **~6 GB** |

Note : Ollama charge et décharge les modèles dynamiquement. Les deux modèles
ne sont pas forcément en mémoire simultanément, ce qui réduit l'utilisation
réelle.


---


## 5. Intelligence artificielle — Stratégie locale

### 5.1 Pourquoi le tout local

| Critère | Cloud (Claude API, GPT, etc.) | Local (Ollama) |
|---|---|---|
| Coût mensuel | 50-300 €/mois | 0 € |
| Confidentialité | Documents envoyés sur serveurs tiers | Tout reste sur la machine |
| RGPD | Complexe (CNI, adresses envoyées) | Aucun problème |
| Dépendance | API peut changer, augmenter les prix | Autonomie totale |
| Disponibilité | Dépend d'internet | Fonctionne hors ligne |
| Performance | Plus rapide | Suffisant pour le volume visé |

Le choix du tout local est motivé principalement par :
- La **confidentialité des données** (CNI, adresses personnelles, données véhicule)
- L'**absence de coût récurrent**
- L'**indépendance** vis-à-vis des fournisseurs d'API

### 5.2 Modèles sélectionnés

**Qwen2.5-VL:7b (vision) — Classification des documents**

Modèle multimodal (image + texte) de la famille Qwen (Alibaba).
Meilleur modèle vision open source dans la catégorie 7B en 2025-2026.

Utilisation : on envoie l'image du document au modèle avec un prompt de
classification. Il retourne le type de document et un score de confiance.

Avantages :
- Comprend les documents français
- 7 milliards de paramètres = tourne sur 6 GB de RAM
- Licence Apache 2.0 (usage commercial libre)
- Précision suffisante pour distinguer 8 types de documents

**Qwen2.5:7b (texte) — Extraction structurée**

Modèle texte pur de la famille Qwen. Utilisé pour transformer le texte brut
OCR en données JSON structurées via des prompts spécifiques à chaque type
de document.

Utilisation : on envoie le texte OCR + un prompt structuré demandant
d'extraire les champs spécifiques (immatriculation, VIN, nom, etc.).
Le modèle retourne un objet JSON.

### 5.3 Pipeline IA

```
Document (image/PDF)
       │
       ▼
┌──────────────┐
│  ÉTAPE 1     │     Qwen2.5-VL (vision)
│  Classifier  │──►  "Ce document est une carte_grise (conf: 0.97)"
└──────┬───────┘
       │
       ▼
┌──────────────┐
│  ÉTAPE 2     │     OpenCV
│  Preprocess  │──►  Redressement, contraste, débruitage
└──────┬───────┘
       │
       ▼
┌──────────────┐
│  ÉTAPE 3     │     Surya OCR
│  OCR         │──►  "A AB-123-CD\nB 15/03/2020\nC.1 DUPONT Jean..."
└──────┬───────┘
       │
       ▼
┌──────────────┐
│  ÉTAPE 4     │     Qwen2.5 (texte) + prompt spécifique carte grise
│  Extraire    │──►  {"A_immatriculation": "AB-123-CD",
└──────────────┘      "B_date_premiere_immat": "15/03/2020",
                      "C1_titulaire_nom": "DUPONT",
                      "C1_titulaire_prenom": "Jean",
                      "E_vin": "VF1RFB00X12345678", ...}
```

**Pourquoi 2 étapes IA (vision + texte) au lieu d'une seule :**

La vision (Qwen2.5-VL) est excellente pour classifier un document dans son
ensemble mais peut mal lire les petits caractères d'une carte grise.
Surya OCR capture tout le texte avec précision, puis le LLM texte
(Qwen2.5) structure proprement les données. Cette approche en deux temps
est plus fiable qu'une extraction directe par vision.

### 5.4 OCR — Surya

Surya est le meilleur OCR open source disponible en 2025-2026. Il surpasse
Tesseract et EasyOCR sur les documents français.

| Capacité | Détail |
|---|---|
| Langues | Français natif, 90+ langues |
| Layout | Détecte tableaux, zones texte, colonnes |
| Qualité | Supérieur à Tesseract sur documents complexes |
| Vitesse | 2-5 secondes par page sur Apple Silicon (MPS) |
| Licence | GPL 3.0 (usage interne OK) |

Le preprocessing OpenCV est appliqué avant l'OCR pour améliorer les résultats
sur les photos prises au smartphone :
- Redressement de perspective (correction de l'angle)
- Amélioration du contraste (documents pâles ou surexposés)
- Débruitage (bruit numérique, artefacts de compression)
- Binarisation adaptative (texte noir sur fond blanc)


---


## 6. Modules fonctionnels

### 6.1 Module Classification (`src/classification/`)

**Entrée :** Image ou PDF d'un document
**Sortie :** Type de document + score de confiance

Types reconnus :
- `carte_grise` — Certificat d'immatriculation
- `cni` — Carte nationale d'identité
- `passeport` — Passeport
- `justificatif_domicile` — Facture EDF, eau, téléphone, avis d'impôt
- `certificat_cession` — CERFA 15776
- `controle_technique` — Procès-verbal de contrôle technique
- `attestation_assurance` — Attestation d'assurance du véhicule
- `facture_vente` — Facture de vente du véhicule

Le modèle Qwen2.5-VL reçoit l'image avec un prompt lui demandant de
classifier parmi ces 8 types et retourner un JSON avec le type et le
score de confiance.

### 6.2 Module OCR (`src/ocr/`)

**Entrée :** Image d'un document
**Sortie :** Texte brut extrait + coordonnées des zones de texte

Deux sous-modules :
- `preprocessor.py` : amélioration de l'image avant OCR (OpenCV)
- `engine.py` : extraction du texte via Surya OCR

### 6.3 Module Extraction (`src/extraction/`)

**Entrée :** Texte brut OCR + type de document
**Sortie :** Données structurées JSON

Un extracteur spécifique par type de document, chacun avec son prompt
optimisé pour Qwen2.5 :

**Carte grise — Champs extraits :**

| Champ | Code | Exemple |
|---|---|---|
| Immatriculation | A | AB-123-CD |
| Date 1ère immatriculation | B | 15/03/2020 |
| Titulaire nom | C.1 | DUPONT |
| Titulaire prénom | C.1 | Jean |
| Adresse | C.3 | 12 rue de la Paix 75002 Paris |
| Marque | D.1 | YAMAHA |
| Type variante version | D.2 | RN491 |
| Dénomination commerciale | D.3 | MT-07 |
| VIN | E | JYARN491000012345 |
| Masse max en charge | F.1 | 380 |
| Genre national | J.1 | MTL |
| Carrosserie CE | J.2 | — |
| Cylindrée | P.1 | 689 |
| Puissance kW | P.2 | 55 |
| Énergie | P.3 | ES |
| Puissance fiscale | P.6 | 4 |
| Places assises | S.1 | 2 |
| CO2 | V.7 | 0 |
| Formule | — | 2020AB12345 |

**CNI — Champs extraits :**
Nom, prénom, date de naissance, lieu de naissance, numéro du document,
date de délivrance, date de validité, adresse (si CNI format carte).

**Certificat de cession — Champs extraits :**
Nom et adresse du vendeur, nom et adresse de l'acheteur, date et heure
de cession, immatriculation, VIN, marque, kilométrage, signature.

**Justificatif de domicile — Champs extraits :**
Nom du titulaire, adresse complète (numéro, rue, code postal, ville),
date du document.

**Contrôle technique — Champs extraits :**
Date du contrôle, résultat (favorable / défavorable), date limite de
validité, immatriculation, kilométrage.

### 6.4 Module Véhicule (`src/vehicle/`)

**Entrée :** VIN et/ou immatriculation et/ou CNIT
**Sortie :** Fiche technique complète du véhicule

Trois sources de données interrogées :

**Source 1 — Base types mines (data.gouv.fr)**

Le fichier officiel des types mines contient environ 500 000 entrées.
Il est téléchargeable gratuitement sur data.gouv.fr et importé dans
PostgreSQL. La recherche se fait par CNIT (Code National d'Identification
du Type), extrait du champ D.2 de la carte grise.

Données disponibles : marque, dénomination commerciale, genre, carrosserie,
énergie, cylindrée, puissance fiscale, puissance kW, CO2, nombre de places,
poids à vide, PTAC.

**Source 2 — Base stock interne (optionnelle)**

Fonctionnalité optionnelle, désactivée par défaut. L'entreprise agissant
en tant qu'intermédiaire, les véhicules traités ne sont généralement pas
dans son propre stock. Cette source n'est utile que si un professionnel
(vendeur, concessionnaire) enregistre ses véhicules en amont dans le système.
Quand elle est activée, la recherche se fait par VIN ou immatriculation dans
la table PostgreSQL `vehicules_stock`.

**Source 3 — Décodeur VIN**

Le VIN (Vehicle Identification Number) est un code de 17 caractères qui
encode le constructeur, le pays d'origine, l'année-modèle et le numéro
de série. Le décodeur utilise une table WMI (World Manufacturer Identifier)
pour identifier le constructeur à partir des 3 premiers caractères.

Exemples : VF1 = Renault, JYA = Yamaha, WBA = BMW, ZDM = Ducati.

Le moteur de recherche (`search.py`) combine ces sources et retourne
une fiche technique fusionnée. Par défaut, seules les sources 1 (types mines)
et 3 (VIN) sont utilisées. La source 2 (stock) est activable en option.

### 6.5 Module Taxes (`src/taxes/`)

**Entrée :** Puissance fiscale, région, énergie, CO2, masse, genre, date
**Sortie :** Détail des taxes Y1 à Y6 + total

| Taxe | Calcul | Exemple |
|---|---|---|
| Y1 — Taxe régionale | Puissance fiscale × tarif régional | 4 CV × 43€ = 172€ |
| Y3 — Formation pro | Y1 × taux fixe | 172 × 0.01 = 1.72€ |
| Y4 — Malus CO2 | Barème annuel selon g/km | 0€ (moto) |
| Y5 — Malus masse | Barème si > 1800 kg | 0€ (moto) |
| Y6 — Taxe fixe | Redevance acheminement | 11€ |
| **Total** | | **184.72€** |

Exonérations gérées :
- Véhicules électriques (EL) et hydrogène (HY) : exonération Y1
- Motos : pas de malus CO2 ni de malus masse
- Remorques : calcul spécifique sur le PTAC

Les barèmes sont stockés dans `config/tax_rates.py` et mis à jour
annuellement.

### 6.6 Module CERFA (`src/cerfa/`)

**Entrée :** Données extraites + données véhicule + taxes calculées
**Sortie :** Fichier PDF CERFA 13750 pré-rempli

Le CERFA 13750*07 (demande de certificat d'immatriculation) est un PDF
officiel avec des champs de formulaire AcroForm. Le module utilise la
bibliothèque `fillpdf` pour remplir ces champs programmatiquement.

Structure du CERFA :
- **Cadre A** — Demandeur : nom, prénom, date de naissance, adresse
  (données issues de la CNI et du justificatif de domicile)
- **Cadre B** — Véhicule : immatriculation, VIN, marque, genre, énergie,
  puissance (données issues de la carte grise et de la base technique)
- **Cadre C** — Nature de l'opération : case cochée selon le type
  (changement de titulaire, première immatriculation, duplicata, etc.)
- **Taxes** — Montants Y1 à Y6 pré-remplis

Le mapping entre les données extraites et les noms des champs AcroForm
est défini dans `config/field_mappings.py`. Les noms exacts des champs
sont obtenus par inspection du PDF officiel.

### 6.7 Module Validation (`src/validation/`)

**Entrée :** Ensemble des documents d'un dossier avec leurs données extraites
**Sortie :** Rapport de validation (erreurs bloquantes + avertissements)

Vérifications effectuées :

| Vérification | Type | Détail |
|---|---|---|
| VIN cohérent | Erreur | Le VIN de la carte grise doit correspondre à celui du certificat de cession |
| Immatriculation cohérente | Erreur | L'immatriculation carte grise doit correspondre à celle de la cession |
| Nom acheteur = nom CNI | Warning | Comparaison fuzzy (tolérance aux accents, casse) |
| Justificatif < 6 mois | Erreur | La date du justificatif de domicile doit être récente |
| CNI non expirée | Erreur | La date de validité de la CNI ne doit pas être dépassée |
| CT valide | Erreur | Si véhicule > 4 ans et pas de moto < 125cc, CT obligatoire et valide |
| Documents complets | Warning | Vérifie que tous les documents obligatoires sont présents |

### 6.8 Module Email (`src/email_handler/`)

**Entrée :** Configuration IMAP
**Sortie :** Dossiers créés avec pièces jointes extraites

- `receiver.py` : connexion IMAP, polling périodique, extraction des pièces
  jointes, création d'un répertoire par dossier
- `sender.py` : envoi d'accusés de réception, relances pour documents
  manquants, notifications de traitement terminé

### 6.9 Module Pipeline (`src/pipeline/`)

L'orchestrateur séquentiel qui enchaîne tous les modules pour traiter
un dossier complet. En phase de développement, c'est ce module qui
coordonne le flux. En production, OpenClaw prend le relais.


---


## 7. OpenClaw — Orchestration autonome en production

### 7.1 Rôle d'OpenClaw

OpenClaw est un agent IA autonome open source (MIT, 280k+ stars GitHub)
créé par Peter Steinberger. Il est utilisé **uniquement en production**,
pas pendant le développement.

Son rôle : remplacer l'orchestrateur Python (`pipeline/orchestrator.py`)
par un agent intelligent qui :
- **Surveille** en permanence la boîte email
- **Déclenche** automatiquement le traitement à chaque nouvel email
- **Décide** quoi faire en cas de problème (document manquant, erreur OCR)
- **Communique** avec la personne habilitée et l'opérateur
- **S'adapte** aux situations imprévues grâce au raisonnement du LLM

### 7.2 Différence avec un script Python classique

| Aspect | Pipeline Python | OpenClaw |
|---|---|---|
| Exécution | Script lancé manuellement ou par cron | Agent toujours actif |
| Logique | if/else rigide | Raisonnement LLM adaptatif |
| Erreur inattendue | Crash ou log | OpenClaw raisonne et réagit |
| Relance personne habilitée | Code spécifique à écrire | OpenClaw compose un email contextualisé |
| Notifications | Templates figés | Messages adaptés au contexte |
| Canaux | Email uniquement | Email + WhatsApp + Slack + Discord |
| Monitoring | Logs fichier | Interface OpenClaw intégrée |

### 7.3 Skills OpenClaw

Chaque module Python développé en phases 1-7 est encapsulé en "skill"
OpenClaw en phase 8. Un skill est un plugin que l'agent peut appeler
quand il en a besoin.

```
skills/
├── skill-classify/       ← appelle src/classification/
├── skill-ocr/            ← appelle src/ocr/
├── skill-extract/        ← appelle src/extraction/
├── skill-vehicle/        ← appelle src/vehicle/
├── skill-taxes/          ← appelle src/taxes/
├── skill-cerfa/          ← appelle src/cerfa/
├── skill-validate/       ← appelle src/validation/
└── skill-notify/         ← appelle src/email_handler/
```

Chaque skill contient :
- Un `manifest.json` décrivant ses entrées/sorties (pour qu'OpenClaw sache
  quand et comment l'utiliser)
- Un `handler.py` qui fait le pont entre OpenClaw et le module Python

### 7.4 Configuration OpenClaw

OpenClaw se connecte à Ollama en local :

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

Contexte minimum recommandé : 64k tokens (le system prompt, les skills,
la mémoire et l'historique partagent la même fenêtre de contexte).

### 7.5 Flux opérationnel avec OpenClaw

```
1. La personne habilitée envoie un email avec les pièces du client
2. OpenClaw détecte l'email via son canal IMAP
3. OpenClaw raisonne : "J'ai reçu un email avec 4 pièces jointes,
   je vais les classifier"
4. → Appelle skill-classify sur chaque PJ
5. OpenClaw raisonne : "J'ai identifié une carte grise, une CNI,
   un certificat de cession et un justificatif. Il ne manque rien."
6. → Appelle skill-ocr puis skill-extract sur chaque document
7. → Appelle skill-vehicle avec le VIN extrait
8. → Appelle skill-validate pour vérifier la cohérence
9. OpenClaw raisonne : "Tout est cohérent, je calcule les taxes
   et je génère le CERFA"
10. → Appelle skill-taxes puis skill-cerfa
11. → Appelle skill-notify pour alerter l'opérateur
12. L'opérateur ouvre le dashboard, vérifie 2-3 min, valide
13. OpenClaw envoie le CERFA pré-rempli par email à la personne habilitée
14. La personne habilitée soumet le CERFA à l'ANTS
```

Si un document manque :
```
5b. OpenClaw raisonne : "Il manque le justificatif de domicile.
    Je vais relancer la personne habilitée."
    → Appelle skill-notify avec type "relance_documents"
    → Compose un email : "Bonjour, le dossier CG-2026-0042
      est incomplet. Merci de nous transmettre le justificatif
      de domicile de moins de 6 mois du client."
    → Met le dossier en statut "documents_manquants"
    → Reprendra le traitement quand le document arrivera
```


---


## 8. Modèle de données

### 8.1 Schéma relationnel

```
┌──────────────┐     ┌──────────────────┐     ┌──────────────┐
│   dossiers   │────►│    documents     │     │ types_mines  │
│──────────────│     │──────────────────│     │──────────────│
│ id           │     │ id               │     │ cnit (PK)    │
│ reference    │     │ dossier_id (FK)  │     │ marque       │
│ email_source │     │ type_document    │     │ denomination │
│ client_nom   │     │ fichier_path     │     │ genre        │
│ client_email │     │ donnees_json     │     │ energie      │
│ immatricul.  │     │ confidence       │     │ cylindree    │
│ vin          │     │ ocr_texte_brut   │     │ puiss_fisc.  │
│ type_operat. │     │ created_at       │     │ co2          │
│ region       │     └──────────────────┘     │ nb_places    │
│ statut       │                               │ ptac         │
│ donnees_json │     ┌──────────────────┐     │ date_debut   │
│ taxes_json   │     │ vehicules_stock  │     │ date_fin     │
│ cerfa_path   │     │──────────────────│     └──────────────┘
│ created_at   │     │ id               │
│ updated_at   │     │ vin (UNIQUE)     │
└──────────────┘     │ immatriculation  │
       │              │ cnit (FK) ───────────────────┘
       └─────────────►│ marque           │
                      │ modele           │
                      │ prix_vente       │
                      │ statut           │
                      └──────────────────┘
```

### 8.2 Volumétrie estimée

| Table | Nombre d'entrées | Croissance |
|---|---|---|
| types_mines | ~500 000 | Fixe (import annuel) |
| vehicules_stock | ~50-200 | Variable selon stock |
| dossiers | ~200/mois | +200/mois |
| documents | ~1 000/mois | ~5 docs/dossier |


---


## 9. Sécurité et confidentialité

### 9.1 Données sensibles traitées

Le système manipule des données personnelles sensibles :
- Noms, prénoms, dates de naissance
- Numéros de CNI et passeport
- Adresses personnelles
- Numéros d'immatriculation et VIN

### 9.2 Mesures de protection

| Mesure | Détail |
|---|---|
| **Traitement 100% local** | Aucune donnée ne quitte le Mac Mini |
| **Pas d'API cloud** | Pas de transmission à Google, OpenAI, Anthropic, etc. |
| **Pas d'envoi de données** | Les LLM tournent localement via Ollama |
| **Accès restreint** | Dashboard accessible uniquement en réseau local |
| **Fichiers sur disque** | Documents stockés dans `data/dossiers/` sur le Mac Mini |
| **BDD locale** | PostgreSQL accessible uniquement depuis localhost |
| **Variables d'environnement** | Mots de passe IMAP stockés dans `.env` (non versionné) |

### 9.3 Conformité RGPD

Le fait que tout le traitement soit local simplifie considérablement la
conformité RGPD :
- Pas de sous-traitant cloud à déclarer
- Pas de transfert de données hors UE
- Données conservées uniquement le temps nécessaire au traitement
- Suppression possible à la demande du client

### 9.4 Sécurité OpenClaw

OpenClaw tourne en local et ne communique qu'avec les services configurés
(Ollama, PostgreSQL, IMAP). Précautions à prendre :
- Ne pas installer de skills tiers non vérifiés depuis le registre communautaire
- Utiliser uniquement les skills développés en interne
- Configurer le pare-feu pour bloquer les accès entrants non autorisés


---


## 10. Plan de développement

### 10.1 Vue d'ensemble

```
DÉVELOPPEMENT (Python classique)          OPÉRATIONNEL (OpenClaw)
─────────────────────────────────         ─────────────────────────
Phase 1 │ Fondations                      Phase 8 │ Intégration OpenClaw
Phase 2 │ OCR + Classification            Phase 9 │ Tests + Production
Phase 3 │ Recherche véhicule
Phase 4 │ Taxes + CERFA
Phase 5 │ Cross-validation
Phase 6 │ Email + notifications
Phase 7 │ Dashboard Streamlit
```

### 10.2 Détail des phases

**Phase 1 — Fondations**
Installation PostgreSQL, création des tables, import de la base types mines,
installation des dépendances Python, vérification Ollama et téléchargement
des modèles.

**Phase 2 — OCR + Classification + Extraction**
Cœur technique du système. Preprocessing OpenCV, intégration Surya OCR,
classification par Qwen2.5-VL, extraction structurée par Qwen2.5 avec
prompts spécifiques par type de document. Tests sur documents réels.

**Phase 3 — Recherche véhicule**
Décodeur VIN, requêtes base types mines, gestion du stock interne,
moteur de recherche multi-sources.

**Phase 4 — Taxes + CERFA**
Calcul de toutes les taxes (Y1-Y6) avec gestion des exonérations et cas
particuliers (motos, remorques). Pré-remplissage du CERFA 13750 via fillpdf.

**Phase 5 — Cross-validation**
Vérifications automatiques de cohérence entre tous les documents d'un dossier.
Rapport d'erreurs et d'avertissements.

**Phase 6 — Email + notifications**
Connexion IMAP, extraction des pièces jointes, création automatique de
dossiers, envoi d'accusés de réception et de relances.

**Phase 7 — Dashboard Streamlit**
Interface opérateur pour la validation des dossiers. Vue côte à côte des
documents et des données extraites, champs éditables, indicateurs de
confiance, génération du CERFA final.

**Phase 8 — Intégration OpenClaw**
Installation et configuration d'OpenClaw. Encapsulation de chaque module
Python en skill OpenClaw (manifest.json + handler.py). Configuration du
canal email. Test du flux complet autonome.

**Phase 9 — Production**
Tests unitaires et d'intégration. Tests sur cas réels (voitures, motos,
remorques). Gestion des erreurs et edge cases. Déploiement final.


---


## 11. Analyse économique

### 11.1 Coût du système

**Investissement initial :**

| Poste | Coût |
|---|---|
| Mac Mini M4 16 GB (si pas déjà possédé) | ~900 € |
| Développement (temps) | Interne |
| Logiciels et licences | 0 € (tout open source) |

**Coût opérationnel mensuel :**

| Poste | Coût |
|---|---|
| OpenClaw | 0 € |
| IA (Ollama) | 0 € |
| OCR (Surya) | 0 € |
| PostgreSQL | 0 € |
| Hébergement | 0 € (machine sur site) |
| Électricité Mac Mini | ~5-10 € |
| **Total mensuel** | **~5-10 €** |

### 11.2 Gains estimés

**Hypothèse : 200 dossiers/mois**

| Métrique | Avant | Après | Gain |
|---|---|---|---|
| Temps par dossier | 15-20 min | 2-3 min (validation seule) | ~15 min |
| Temps mensuel total | ~60 heures | ~10 heures | **~50 heures** |
| Erreurs de saisie | ~5-10% | ~0.5% (validation IA) | **÷10** |
| Délai traitement | 24-48h | < 1h (si validation rapide) | **÷24** |

**Valeur du gain de temps :**
50 heures × coût horaire chargé (~25-35 €) = **1 250 à 1 750 €/mois** économisés.

**Retour sur investissement :**
Le Mac Mini est amorti en moins d'un mois sur les seules économies de temps.

### 11.3 Comparaison avec les alternatives

| Solution | Coût mensuel | Confidentialité | Autonomie |
|---|---|---|---|
| **Notre système (local)** | **~5-10 €** | **Totale** | **Totale** |
| Service SaaS carte grise | 50-200 €/mois | Données chez le prestataire | Dépendant |
| IA cloud (Claude/GPT API) | 50-150 €/mois | Documents envoyés au cloud | Dépendant des API |
| Saisie manuelle (statu quo) | 0 € (mais coût en temps) | OK | OK |


---


## 12. Risques et mitigations

| Risque | Probabilité | Impact | Mitigation |
|---|---|---|---|
| OCR imprécis sur photos smartphone | Moyenne | Moyen | Preprocessing OpenCV + fallback DocTR + correction dashboard |
| LLM 7B insuffisant pour extraction complexe | Faible | Moyen | Fallback Mistral-Small:22b (si RAM dispo) ou correction manuelle |
| Format CERFA change (nouvelle version) | Faible | Fort | Remplacer le template PDF + mettre à jour le mapping |
| Barèmes taxes changent | Certaine (annuel) | Moyen | Mise à jour annuelle de `config/tax_rates.py` |
| Base types mines obsolète | Faible | Moyen | Ré-import annuel depuis data.gouv.fr |
| Panne Mac Mini | Faible | Fort | Sauvegardes régulières de la BDD + documents |
| Vulnérabilité OpenClaw | Faible | Moyen | N'utiliser que des skills internes, pas de plugins tiers |
| RAM insuffisante (2 modèles simultanés) | Faible | Moyen | Ollama gère le swap de modèles automatiquement |
| Changement réglementaire majeur | Faible | Fort | Architecture modulaire = adaptation ciblée |


---


## 13. Évolutions futures

### Court terme (après mise en production)
- Gestion multi-personnes habilitées (plusieurs expéditeurs)
- Ajout canal WhatsApp pour réception documents
- Notification Slack/Discord pour l'équipe

### Moyen terme
- Application mobile pour prise de photo guidée des documents
- Tableau de bord statistiques (volume, temps de traitement, taux d'erreur)
- Gestion multi-utilisateurs (plusieurs opérateurs)
- Historique client (retrouver un ancien dossier)

### Long terme
- Extension à d'autres démarches administratives (permis, déclarations)
- Modèle IA fine-tuné sur les documents carte grise français
- API pour intégration avec le logiciel de gestion commerciale existant


---


## 14. Conclusion

Ce système d'automatisation des demandes de carte grise représente une
solution complète, économique et respectueuse de la confidentialité des
données.

**Points clés :**

- **Entièrement local et open source** : zéro coût de licence, zéro
  dépendance cloud, données protégées
- **IA performante sur du matériel grand public** : les modèles 7B sur
  Apple Silicon offrent un rapport qualité/coût imbattable
- **Architecture modulaire** : chaque brique est indépendante, testable
  et remplaçable
- **Autonomie en production** : OpenClaw orchestre le flux de bout en bout,
  l'opérateur ne fait que valider
- **ROI immédiat** : 50 heures économisées par mois dès la mise en production

Le projet est structuré pour un développement progressif, phase par phase,
avec des livrables testables à chaque étape. La transition vers la production
se fait naturellement en encapsulant les modules Python dans des skills
OpenClaw.
