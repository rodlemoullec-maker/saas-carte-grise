# Imatra — Whitepaper Complet

**Plateforme SaaS B2B d'automatisation des demandes d'immatriculation pour les professionnels de l'automobile**

*Version 3.0 — Avril 2026*

---

## Table des matieres

1. [Resume executif](#1-resume-executif)
2. [Le marche et son contexte](#2-le-marche-et-son-contexte)
3. [Le probleme](#3-le-probleme)
4. [La solution Imatra](#4-la-solution-imatra)
5. [Architecture technique](#5-architecture-technique)
6. [Moteur de regles et controles](#6-moteur-de-regles-et-controles)
7. [Pipeline de traitement](#7-pipeline-de-traitement)
8. [Parcours utilisateurs](#8-parcours-utilisateurs)
9. [Generation Cerfa automatisee](#9-generation-cerfa-automatisee)
10. [Conformite reglementaire et RGPD](#10-conformite-reglementaire-et-rgpd)
11. [Modele economique](#11-modele-economique)
12. [Positionnement concurrentiel](#12-positionnement-concurrentiel)
13. [Securite et gardes-fous](#13-securite-et-gardes-fous)
14. [Roadmap](#14-roadmap)
15. [Metriques du projet](#15-metriques-du-projet)
16. [Annexes](#16-annexes)

---

## 1. Resume executif

Imatra est une plateforme SaaS B2B qui automatise de bout en bout les demandes de certificat d'immatriculation (carte grise) pour les professionnels de l'automobile en France : concessionnaires, garages, revendeurs, mandataires et agents habilites SIV.

### Le constat

Le marche francais compte plus de **32 000 professionnels habilites SIV** et **104 000 entreprises automobiles au total** (INSEE). Chaque professionnel traite entre 50 et 500 demandes de carte grise par an. Chaque dossier mobilise en moyenne **30 a 45 minutes** de travail administratif manuel : collecte de documents, verification de conformite, remplissage de formulaires Cerfa, soumission au Systeme d'Immatriculation des Vehicules (SIV), suivi.

Le taux de rejet SIV oscille entre **15% et 25%** des soumissions. Chaque rejet coute au professionnel entre 20 et 40 minutes supplementaires de diagnostic, correction et resoumission — sans parler de l'insatisfaction client.

### La reponse

Imatra reduit le temps de traitement a **moins de 5 minutes** par dossier grace a un moteur d'automatisation qui enchaine :
- **OCR intelligent** (Google Document AI + fallback Claude IA)
- **Classification automatique** de 31 types de documents
- **Extraction structuree** des donnees cles
- **38 regles de verrouillage** (blocage ROUGE)
- **21 controles de coherence croisee** entre documents
- **Diagnostic tri-couleur** VERT / ORANGE / ROUGE
- **Estimation des taxes** d'immatriculation
- **Generation automatique** des Cerfa pre-remplis (13749 VN, 13750 VO)
- **Collecte client par SMS** avec parcours mobile securise

### Deux offres complementaires

| Offre | Cible | Principe |
|-------|-------|----------|
| **SaaS** | Pros deja habilites SIV | Dossier pret a soumettre — le pro soumet lui-meme dans son SIV |
| **Full Service** | Pros non habilites SIV | Prise en charge complete, de la verification a la soumission |

### Chiffres cles

- **12 EUR** par dossier moto, **14 EUR** par dossier voiture (honoraires plateforme)
- **5 dossiers d'essai** sans avance de frais
- **Phase 0 + Phase 1 absorbees** par la plateforme (~0,50 EUR)
- Objectif : **< 2% de rejet SIV** contre 15-25% actuellement

---

## 2. Le marche et son contexte

### 2.1 Le cadre reglementaire francais

Depuis la reforme de 2017 et la fermeture des guichets prefectures, toutes les demarches d'immatriculation s'effectuent en ligne via le **Systeme d'Immatriculation des Vehicules (SIV)** de l'ANTS. Deux voies sont possibles :

1. **Le particulier** realise lui-meme sa demarche sur le site de l'ANTS
2. **Un professionnel habilite SIV** effectue la demarche pour le compte du client

L'habilitation SIV est delivree par la prefecture a tout professionnel de l'automobile justifiant d'une activite reguliere et remplissant les conditions fixees par l'arrete du 14 octobre 2009.

### 2.2 Les acteurs du marche

| Segment | Volume estime | Habilitation SIV |
|---------|--------------|------------------|
| Concessionnaires automobiles | ~6 000 | Oui (majorite) |
| Garages et revendeurs VO | ~18 000 | Variable |
| Mandataires automobiles | ~3 000 | Oui |
| Agents SIV independants (points CG, tabacs) | ~5 000 | Oui |
| Petits garages / revendeurs motos | ~15 000+ | Rarement |
| **Total entreprises automobiles** | **~104 000** | — |
| **Total habilites SIV** | **~32 000** | Oui |

### 2.3 Volume de transactions

Le SIV traite plus de **10 millions d'operations d'immatriculation par an**, dont :
- ~5,5 millions de vehicules d'occasion
- ~2 millions de vehicules neufs
- ~2,5 millions d'autres operations (changement d'adresse, duplicata, etc.)

Les professionnels interviennent sur une part significative de ces operations, en particulier pour les vehicules neufs (quasi-100% via pros) et une part croissante des occasions.

### 2.4 La douleur du marche

Le processus actuel pour un professionnel :

```
Vente vehicule
    → Collecte manuelle des documents client (CNI, permis, domicile, etc.)
    → Verification visuelle de chaque document
    → Remplissage manuel du Cerfa (13749 VN ou 13750 VO)
    → Saisie manuelle dans le SIV (50+ champs)
    → Attente retour SIV
    → En cas de rejet : diagnostic, relance client, correction, resoumission
    → En cas d'acceptation : generation CPI, envoi au client
```

**Temps moyen** : 30-45 minutes par dossier conforme, 60-90 minutes en cas de rejet.

**Principaux irritants** :
- Verification manuelle fastidieuse et sujette a erreur
- Rejets SIV frequents (15-25%) sur des erreurs evitables
- Collecte des documents client chronophage (appels, relances)
- Remplissage repetitif des memes formulaires Cerfa
- Aucune visibilite temps reel sur la completude du dossier

---

## 3. Le probleme

### 3.1 Complexite documentaire

Une demande de carte grise n'est pas un formulaire simple. Selon le cas (vehicule neuf ou occasion, acheteur particulier, societe, mineur, etranger, heberge, co-titulaires, vehicule importe, gage, etc.), le dossier peut necessiter jusqu'a :

- **31 types de documents** differents
- **20 scenarios** de cas d'usage distincts, chacun avec ses specificites
- **38 criteres de verrouillage** pouvant bloquer un dossier
- **21 regles de coherence croisee** entre documents

Le professionnel doit maitriser l'ensemble de ces cas sans outil dedie. La moindre erreur — un VIN mal recopie, une CNI expiree de 3 jours, un co-titulaire oublie — genere un rejet SIV.

### 3.2 Le cout des rejets

| Impact | Detail |
|--------|--------|
| **Temps perdu** | 20-40 min par rejet (diagnostic + correction + resoumission) |
| **Client mecontent** | Delai supplementaire, perte de confiance |
| **Cout non recuperable** | Le temps administratif n'est generalement pas facture |
| **Risque juridique** | Un dossier mal constitue engage la responsabilite du pro habilite |
| **Repetition** | Les memes erreurs se reproduisent sans systeme de prevention |

Avec un taux de rejet de 20% et 200 dossiers/an, un professionnel perd **40 a 80 heures par an** sur des corrections evitables.

### 3.3 Risques de fraude et conformite

Le SIV est un systeme sensible. Les professionnels habilites portent une responsabilite legale sur chaque dossier soumis. Les risques :
- Faux documents d'identite
- Vehicules voles ou gages non declares
- Vehicules sous OTCI (Opposition au Transfert du Certificat d'Immatriculation)
- VEC/VEI (Vehicules Economiquement ou Irremediablement Endommmages)
- Usurpation d'identite

Le controle humain seul ne peut pas garantir la detection systematique de ces cas a grande echelle.

---

## 4. La solution Imatra

### 4.1 Proposition de valeur

Imatra est un **assistant administratif post-vente invisible** pour les professionnels de l'automobile. Il ne remplace pas le professionnel — il elimine le travail administratif repetitif pour que le pro se concentre sur son metier : vendre et entretenir des vehicules.

**Ce que fait Imatra :**
- Collecte les documents automatiquement (du pro et/ou du client via SMS)
- Lit et comprend chaque document par OCR + IA
- Verifie la conformite en temps reel (38 regles + 21 croisements)
- Alerte le pro sur les problemes avant la soumission
- Pre-remplit les Cerfa automatiquement
- Estime les taxes d'immatriculation
- Livre un dossier pret a soumettre (SaaS) ou soumet directement (Full Service)

**Ce que ne fait pas Imatra :**
- Il ne se substitue pas au professionnel habilite (le pro reste responsable)
- Il ne soumet pas au SIV sans validation explicite du pro
- Il n'est pas un service de carte grise en ligne pour particuliers
- Il ne gere pas le controle technique (hors perimetre)

### 4.2 Les trois profils professionnels

Imatra s'adapte a trois types de professionnels, chacun avec un parcours distinct :

#### Profil 1 : Vendeur habilite SIV

Le cas le plus simple. Le vendeur a sa propre habilitation SIV et soumet ses dossiers lui-meme.

```
Vendeur → Cree le dossier dans Imatra
       → Depose les docs vehicule (COC/CG barree, facture)
       → Envoie un lien SMS au client pour les docs personnels
       → Client uploade CNI, permis, domicile via le lien
       → Imatra verifie tout en temps reel
       → Diagnostic VERT : dossier pret
       → Vendeur telecharge le Cerfa pre-rempli + dossier complet
       → Vendeur soumet dans son SIV
```

**Tarif** : 14 EUR/dossier voiture, 12 EUR/dossier moto.

#### Profil 2 : Vendeur non habilite SIV

Le vendeur n'a pas d'habilitation SIV. Il travaille avec un agent habilite qui soumet pour lui.

```
Vendeur → Cree le dossier dans Imatra
       → Depose les docs vehicule
       → Declenche une demande de mandat a son agent
       → Agent recoit la demande (auto ou manuel selon config)
       → Agent genere le mandat client→agent (Cerfa 13757)
       → Vendeur envoie le lien SMS au client
       → Client uploade ses docs + signe les 2 mandats par OTP SMS
       → Vendeur ET agent recoivent le dossier complet
       → Agent verifie, telecharge le ZIP, soumet au SIV
```

**Tarif** : 14 EUR/dossier voiture, 12 EUR/dossier moto (paye par le vendeur).

#### Profil 3 : Agent habilite independant

L'agent habilite utilise Imatra pour ses propres clients ou pour les dossiers transmis par des vendeurs partenaires.

```
Agent → Cree le dossier OU recoit un dossier d'un vendeur partenaire
     → Depose docs vehicule + client (ou delegue au client via SMS)
     → Imatra verifie tout
     → Diagnostic VERT : agent telecharge le dossier
     → Agent soumet dans son SIV
```

**Tarif** : 14 EUR/dossier voiture, 12 EUR/dossier moto.

### 4.3 La double voie de collecte

Imatra offre deux modes de collecte complementaires que le pro utilise selon la situation :

**Voie 1 — Pro-initiee (flux classique)**
Le pro cree le dossier, depose les documents qu'il a, puis envoie un lien SMS au client pour les documents manquants.

**Voie 2 — Client-initiee (URL permanente)**
Chaque pro dispose d'une URL permanente (`imatra.fr/nom-commerce`) qu'il peut afficher sur son site, ses reseaux sociaux, sa vitrine ou ses emails. Le client accede a cette URL, entre ses informations et depose ses documents. Le dossier apparait dans l'espace pro avec le statut "Nouveau — initie par le client".

Les deux voies coexistent. Le pro choisit selon la situation. L'URL permanente genere egalement un benefice SEO : chaque page pro est indexable avec le nom du commerce, la ville et le mot-cle "carte grise".

### 4.4 Checklist interactive temps reel

Le coeur de l'experience pro est une **checklist dynamique** qui se met a jour en temps reel a chaque document depose :

```
CHECKLIST DOSSIER #CG-2026-00042 — Vehicule neuf

[x] Commerce .......................... Cachet et signature enregistres
[x] Vehicule .......................... COC + Facture deposes (VIN: WBA...)
    → Type detecte : VN
    → CNIT : e2*2007/46*0123
    → Verrou vehicule : DEVERROUILLE

[x] Client (depose par le client) ..... CNI OK, Permis OK, Domicile OK
    → Nom : DUPONT Jean-Pierre
    → Alertes : aucune

[x] Cession ........................... Signature auto (cachet pro)

DIAGNOSTIC : VERT — Pret a generer le Cerfa
```

Chaque ligne indique :
- La **source** du document (depose par le pro ou par le client)
- Le **statut** de verification (OK, avertissement, blocage)
- Les **alertes** specifiques (CNI expiree, domicile > 6 mois, nom divergent, etc.)

### 4.5 Le diagnostic tri-couleur

Un dossier carte grise est conforme ou il ne l'est pas. Il n'y a pas de "75% bon". Le moteur produit un diagnostic clair :

| Couleur | Condition | Action |
|---------|-----------|--------|
| **VERT** | 0 verrouillage, 0 avertissement | Dossier pret — le pro peut generer le Cerfa et soumettre |
| **ORANGE** | 0 verrouillage, ≥1 avertissement | Le pro peut continuer apres verification (CT bientot expire, OCR moyen, assurance provisoire < 7 jours) |
| **ROUGE** | ≥1 verrouillage | Dossier bloque — le pro voit la liste exacte des blocages avec les actions correctives |

Le pro voit la **liste detaillee des blocages et avertissements**, pas un score abstrait. Chaque blocage indique le code V-XX, le document concerne, et l'action corrective a mener.

---

## 5. Architecture technique

### 5.1 Vue d'ensemble

```
                     ┌─────────────────────────────┐
                     │   PROFESSIONNELS             │
                     │   Dashboard React + Vite     │
                     │   (port 5173)                │
                     └──────────────┬───────────────┘
                                    │
                     ┌──────────────▼───────────────┐
                     │   API REST — FastAPI          │
                     │   (Python 3.11+, async)       │
                     │   (port 8001)                 │
                     │                               │
                     │   /dossiers    /documents     │
                     │   /decisions   /batch         │
                     │   /client      /public        │
                     │   /scan        /webhooks      │
                     │   /professionnel              │
                     └──────────────┬───────────────┘
                                    │
              ┌─────────────────────┼─────────────────────┐
              │                     │                     │
    ┌─────────▼──────────┐ ┌───────▼────────┐ ┌──────────▼─────────┐
    │   ENGINE            │ │  INTEGRATIONS  │ │   STORAGE          │
    │                     │ │                │ │                    │
    │   Pipeline 4 phases │ │  Google DocAI  │ │  PostgreSQL (Neon) │
    │   38 regles V-XX    │ │  Claude IA     │ │  AWS S3 (eu-west-3)│
    │   21 regles C-XX    │ │  Stripe        │ │  Redis (cache)     │
    │   Validators        │ │  Twilio SMS    │ │                    │
    │   Normalizers       │ │  INSEE Sirene  │ │                    │
    │   Tax calculator    │ │  BAN Adresses  │ │                    │
    │   Cerfa generator   │ │  HistoVec/CSA  │ │                    │
    └─────────────────────┘ │  NHTSA VIN     │ └────────────────────┘
                            └────────────────┘
```

### 5.2 Stack technique detaillee

| Composant | Technologie | Role |
|-----------|-------------|------|
| **API** | FastAPI (Python 3.11+, async) | API REST, routing, middleware |
| **Frontend pro** | React + TypeScript + Vite + Tailwind CSS v4 | Dashboard professionnel |
| **Frontend client** | React (pages dediees) | Parcours client mobile-first |
| **BDD** | PostgreSQL (Neon, Frankfurt) | Donnees structurees, dossiers, pros |
| **Stockage documents** | AWS S3 (eu-west-3, SSE-AES256) | Documents uploades, chiffres au repos |
| **Cache** | Redis | Cache + file d'attente Celery |
| **Workers** | Celery + Redis | Traitements asynchrones (OCR, batch) |
| **OCR principal** | Google Document AI (EU) | Extraction texte haute confiance |
| **IA fallback** | Anthropic Claude | Classification et extraction complexe |
| **Paiement** | Stripe | Pre-autorisation, debit, SEPA |
| **SMS** | Twilio | Liens securises, OTP, relances |
| **Email** | SMTP (noreply@imatra.fr) | Notifications, relances, factures |
| **Authentification** | JWT (HS256, 60 min) | Tokens d'acces pro |
| **Rate limiting** | Middleware custom | 60 requetes/minute par IP |
| **CI/CD** | GitHub Actions | Tests, build, deploiement |
| **Infrastructure** | Docker + Railway/Render | Deploiement cloud |

### 5.3 Modele de donnees

#### Table `professionnel`

Le professionnel est le client B2B d'Imatra. Le modele supporte les 3 profils :

| Champ | Type | Description |
|-------|------|-------------|
| `id` | UUID | Identifiant unique |
| `raison_sociale` | string | Nom legal de l'entreprise |
| `siret` / `siren` | string | Identifiants legaux |
| `type_compte` | enum | VENDEUR_HABILITE / VENDEUR_NON_HABILITE / AGENT_HABILITE |
| `habilite_siv` | bool | Habilitation SIV active |
| `numero_habilitation` | string | Numero d'habilitation SIV |
| `nom_commerce` | string | Nom commercial (affiche) |
| `slug` | string | URL permanente (imatra.fr/slug) |
| `cachet_path` / `signature_path` | string | Cachet et signature numerises |
| `service_mode` | enum | FULL_SERVICE / SAAS |
| `mode_facturation` | enum | UNITAIRE / ABONNEMENT |
| `assurance_flotte_vn` / `_vo` | bool | Couverture flotte (VN/VO) |
| `relance_mode` | enum | PRO / AUTO |
| `cgv_acceptees` | bool | Acceptation CGV obligatoire |
| `agent_*` | string | Coordonnees agent (pour vendeur non habilite) |

#### Table `dossier`

Chaque dossier represente une demande de carte grise :

| Champ | Type | Description |
|-------|------|-------------|
| `id` | UUID | Identifiant unique |
| `reference` | string | CG-{annee}-{5 chiffres} |
| `type` | enum | VN / VO (detecte automatiquement) |
| `status` | enum | PENDING → ATTENTE_CLIENT → DIAGNOSTIC → CERFA_GENERE → SOUMIS → CLOSED |
| `created_by_source` | enum | PRO / CLIENT |
| `vin` | string | Vehicle Identification Number |
| `immatriculation` | string | Plaque d'immatriculation (VO) |
| `diagnostic` | enum | VERT / ORANGE / ROUGE |
| `blocages` | JSONB | Liste des codes V-XX actifs |
| `cross_check_results` | JSONB | Resultats des 21 croisements |
| `tax_estimate` | JSONB | Estimation taxes (Y1, Y3-Y6) |
| `client_link_token` | string | Token securise lien SMS client |
| `montant_honoraires` | decimal | 12 EUR (moto) / 14 EUR (voiture) |
| `payment_captured` | bool | Paiement effectivement debite |
| `is_personne_morale` | bool | Acheteur = societe |
| `is_mineur` / `is_etranger` | bool | Cas speciaux |
| `relance_nb` / `relance_prochaine` | int/date | Suivi relances automatiques |

#### Table `document`

Chaque document uploade dans un dossier :

| Champ | Type | Description |
|-------|------|-------------|
| `id` | UUID | Identifiant unique |
| `dossier_id` | FK | Rattachement au dossier |
| `type` | enum | CNI, PASSEPORT, PERMIS, COC, FACTURE, CG_BARREE, etc. (17 types) |
| `source` | enum | vendeur / client |
| `extracted_data` | JSONB | Donnees extraites par OCR |
| `quality` | JSONB | Score de confiance, statut, message |
| `file_hash` | string | SHA-256 pour deduplication |

### 5.4 Endpoints API

| Methode | Endpoint | Description |
|---------|----------|-------------|
| POST | `/dossiers` | Creer un dossier |
| GET | `/dossiers` | Lister les dossiers du pro |
| GET | `/dossiers/{id}` | Detail d'un dossier |
| DELETE | `/dossiers/{id}` | Supprimer un dossier |
| POST | `/dossiers/batch` | Creer jusqu'a 50 dossiers en lot |
| POST | `/dossiers/batch/launch` | Lancer le traitement batch |
| POST | `/documents/upload` | Upload + OCR + classification automatique |
| GET | `/decisions/{id}` | Resultat diagnostic Phase 1 |
| POST | `/decisions/{id}/override` | Surcharge agent (ACCEPTE/REJET) |
| POST | `/decisions/{id}/retry` | Relancer le pipeline apres correction |
| GET | `/client/{token}` | Page client (checklist dynamique) |
| POST | `/client/{token}/upload` | Upload document par le client |
| GET | `/public/{slug}` | Page publique du pro (URL permanente) |
| POST | `/public/{slug}/dossier` | Creation dossier client-initie |
| GET | `/scan/{token}` | Page mobile scan QR |
| POST | `/scan/{token}/upload` | Upload via camera mobile |
| PUT | `/professionnel/{id}` | Mise a jour profil pro |
| POST | `/webhooks/stripe` | Callback paiement Stripe |
| POST | `/webhooks/siv` | Callback statut SIV/ANTS |

---

## 6. Moteur de regles et controles

### 6.1 Referentiel documentaire (31 documents)

Le systeme connait 31 types de documents, organises par categorie :

| Categorie | Code | Documents |
|-----------|------|-----------|
| **Formulaires** | D-01 a D-06 | Cerfa 13749 (VN), Cerfa 13750 (VO), Cerfa 15776 (cession), Cerfa 13757 (mandat), Declaration d'achat |
| **Identite acheteur** | D-07 a D-10 | CNI, passeport, titre de sejour, permis de conduire |
| **Justificatif domicile** | D-11 a D-15 | Facture energie, avis d'imposition, quittance loyer, pack hebergement |
| **Vehicule** | D-16 a D-22 | COC, CG barree, CT, assurance, code de cession, recepisse DA, HistoVec |
| **Personne morale** | D-23 a D-25 | Kbis, CNI representant legal, statuts/PV AG |
| **Cas speciaux** | D-26 a D-31 | Livret de famille, autorisation parentale, tutelle/curatelle, deces, mainlevee de gage, attestation pro |

### 6.2 Regles de verrouillage (38 regles V-XX)

Chaque regle V-XX declenche un **blocage ROUGE** si non satisfaite. Le dossier ne peut pas avancer tant que le blocage n'est pas leve.

#### Documents manquants (V-01 a V-10, V-36)

| Code | Regle | Action corrective |
|------|-------|-------------------|
| V-01 | CNI ou passeport absent | Demander la piece d'identite au client |
| V-02 | Permis de conduire absent | Demander le permis (sauf personne morale) |
| V-03 | Justificatif de domicile absent | Demander un justificatif < 6 mois |
| V-04 | COC absent (VN) | Demander le certificat de conformite au constructeur |
| V-05 | Facture de vente absente | Generer ou fournir la facture |
| V-06 | CG barree absente (VO) | Demander la CG originale barree |
| V-07 | Declaration d'achat absente (VO pro) | Generer la DA |
| V-08 | Certificat de cession absent | Generer le Cerfa 15776 |
| V-09 | CT absent ou invalide (VO > 4 ans) | Demander un CT valide |
| V-10 | Assurance absente | Demander l'attestation d'assurance |
| V-36 | Kbis absent (personne morale) | Demander un Kbis < 3 mois |

#### Validite temporelle (V-11 a V-19)

| Code | Regle |
|------|-------|
| V-11 | CNI expiree |
| V-12 | Passeport expire |
| V-13 | Permis expire |
| V-14 | Titre de sejour expire |
| V-15 | Kbis > 3 mois |
| V-16 | CT > 6 mois (date du jour) |
| V-17 | Justificatif de domicile > 6 mois |
| V-18 | Code de cession > 15 jours |
| V-19 | Facture > 6 mois (VN non immatricule) |

#### Qualite documentaire (V-20 a V-23)

| Code | Regle |
|------|-------|
| V-20 | Score OCR < 40% (document illisible) |
| V-21 | Scan tronque (dimensions anormales) |
| V-22 | Document en langue etrangere non traduit |
| V-23 | Rature ou surcharge sur le Cerfa |

#### Coherence (V-24 a V-28)

| Code | Regle |
|------|-------|
| V-24 | VIN incoherent entre documents |
| V-25 | Identite incoherente entre documents (< 85% match) |
| V-26 | Chaine de propriete brisee (vendeur DA ≠ titulaire CG) |
| V-27 | Adresse CG ≠ adresse justificatif domicile |
| V-28 | Date de vente absente ou incoherente |

#### Statut SIV (V-29 a V-32)

| Code | Regle |
|------|-------|
| V-29 | Gage actif sur le vehicule |
| V-30 | OTCI en cours |
| V-31 | VEC ou VEI (vehicule endommage) |
| V-32 | Vol signale |

#### Controles specifiques (V-33 a V-38)

| Code | Regle |
|------|-------|
| V-33 | CG non barree (mention "vendu le" absente) |
| V-34 | Signature manquante sur le Cerfa |
| V-35 | CT defavorable (sans contre-visite) |
| V-37 | KYC echec (controle anti-fraude) |
| V-38 | Categorie permis incompatible avec type vehicule |

### 6.3 Controles de coherence croisee (21 regles C-XX)

Chaque regle compare des donnees extraites de documents differents :

#### Identite (C-01 a C-05)

Fuzzy matching des noms entre documents. Seuils :
- ≥ 97% : correspondance automatique
- 85-96% : avertissement (ORANGE)
- < 85% : blocage (ROUGE)

| Code | Croisement |
|------|------------|
| C-01 | Nom CNI ↔ Nom Cerfa |
| C-02 | Nom CNI ↔ Nom permis |
| C-03 | Nom CNI ↔ Nom assurance |
| C-04 | Nom CNI ↔ Nom justificatif domicile |
| C-05 | Date de naissance CNI ↔ Date Cerfa |

#### Vehicule (C-06 a C-10)

| Code | Croisement |
|------|------------|
| C-06 | VIN COC/CG ↔ VIN Cerfa ↔ VIN facture |
| C-07 | CNIT ↔ base UTAC |
| C-08 | Puissance fiscale COC ↔ Cerfa (±1 CV warning, ±3 CV blocage) |
| C-09 | CO2 WLTP obligatoire pour vehicules post-2021 |
| C-10 | Type vehicule COC ↔ type declare |

#### Chaine de propriete VO (C-11 a C-14)

| Code | Croisement |
|------|------------|
| C-11 | Vendeur DA = titulaire CG |
| C-12 | Chronologie dates CG / DA / cession |
| C-13 | Signatures co-titulaires presentes |
| C-14 | CT valide a la date de saisie SIV |

#### Permis et age (C-15, C-16)

| Code | Croisement |
|------|------------|
| C-15 | Categorie permis ↔ type vehicule (AM, A1, A2, B, etc.) |
| C-16 | Age ↔ categorie autorisee (< 14 : rien, 14-15 : AM, 16-17 : A1, ≥ 18 : B) |

#### Statut SIV (C-17 a C-21)

| Code | Croisement |
|------|------------|
| C-17 | Gage HistoVec ↔ mainlevee fournie |
| C-18 | OTCI HistoVec ↔ resolution |
| C-19 | VEC/VEI HistoVec |
| C-20 | Vol signale HistoVec |
| C-21 | Doublon VIN interne (meme VIN deja dans un dossier en cours) |

### 6.4 Adaptation personne morale

Quand l'acheteur est une societe, le moteur adapte automatiquement :

| Aspect | Personne physique | Personne morale |
|--------|-------------------|-----------------|
| Identite | CNI du client | CNI du representant legal (gerant/president) |
| Permis | Obligatoire | Non exige |
| Domicile | Justificatif < 6 mois | Kbis < 3 mois (siege social) |
| Nom Cerfa | Nom du client | Raison sociale du Kbis |
| Detection | — | Automatique (presence Kbis ou SIREN dans docs) |

---

## 7. Pipeline de traitement

### 7.1 Les 4 phases

Le traitement d'un dossier suit un pipeline en 4 phases sequentielles :

```
PHASE 0          PHASE 1              GO/NO-GO         PHASE 2
HistoVec/CSA  →  OCR + Validation  →  Decision pro  →  Livraison/Soumission
(gratuit)        (~0.50 EUR)          (0 EUR)          (12-14 EUR)
```

#### Phase 0 — Consultation HistoVec/CSA (gratuit)

Avant tout traitement, le systeme interroge les bases publiques :
- **HistoVec** : historique du vehicule (nombre de proprietaires, sinistres declares)
- **CSA** : fichier des vehicules voles
- **Detection** : gages, OTCI, vol, VEC/VEI

Si un probleme est detecte (gage, vol, etc.), le dossier est immediatement bloque avec le code V-XX correspondant. Le pro est informe avant d'investir du temps dans la collecte documentaire.

#### Phase 1 — Pre-qualification (cout absorbe ~0,50 EUR)

Le moteur principal de traitement :

1. **Classification** — Identification automatique du type de document parmi 17 categories, par mots-cles ponderes. Si confiance < 60%, le pro est invite a preciser.

2. **OCR** — Google Document AI extrait le texte brut avec un score de confiance par document (conserve pour V-20).

3. **Extraction structuree** — Des regex metier specialisees extraient les champs structures : VIN, dates, noms, montants, adresses, numeros de serie, etc.

4. **Fallback IA** — Pour les documents complexes ou mal structures, Claude (Anthropic) extrait les donnees en mode conversationnel avec validation de schema JSON.

5. **Normalisation** — Noms (majuscules, accents), adresses (codes postaux, communes), vehicules (detection VN/VO automatique).

6. **Validation** — Application des 38 regles V-XX sur chaque document individuellement.

7. **Croisements** — Application des 21 regles C-XX entre documents.

8. **Diagnostic** — Generation du verdict VERT / ORANGE / ROUGE avec la liste detaillee des blocages et avertissements.

9. **Estimation taxes** — Calcul indicatif des taxes d'immatriculation.

#### GO/NO-GO — Decision du professionnel

Le pro voit le diagnostic complet et decide :
- **VERT** → Lancer le traitement (en un clic)
- **ORANGE** → Verifier les avertissements puis lancer
- **ROUGE** → Corriger les blocages (le systeme indique exactement quoi corriger)

A ce stade, une **pre-autorisation CB** est creee pour le montant des honoraires.

#### Phase 2 — Livraison ou soumission

Selon l'offre :
- **SaaS** : livraison du dossier complet (Cerfa pre-rempli + documents + donnees extraites + checklist + estimation taxes)
- **Full Service** : controle KYC anti-fraude + soumission SIV + generation CPI

Le debit CB n'intervient **qu'a la generation du CPI** (Certificat Provisoire d'Immatriculation). Si le dossier echoue, pas de debit.

### 7.2 OCR et extraction

#### Preprocessing des images

Avant l'OCR, chaque image est pre-traitee :
- Upscaling si dimension < 1500 px
- Conversion en niveaux de gris
- Amelioration du contraste
- Augmentation de la nettete

#### Fournisseurs OCR

| Fournisseur | Role | Region | Confiance |
|-------------|------|--------|-----------|
| **Google Document AI** | OCR principal | EU (Francfort) | Score par bloc + par document |
| **Claude (Anthropic)** | Fallback IA | US (SCCs) | Pour documents complexes |

Le seuil de basculement vers le fallback IA est une confiance OCR < 70%.

#### Extraction par type de document

Chaque type de document possede ses propres regles d'extraction :

| Document | Champs extraits |
|----------|-----------------|
| CNI | Nom, prenom, date naissance, lieu naissance, date expiration, MRZ |
| Passeport | Nom, prenom, nationalite, date naissance, date expiration, MRZ |
| Permis | Nom, prenom, categories, dates delivrance/expiration |
| COC (VN) | Constructeur, CNIT, VIN, type, masse, puissance, CO2, places |
| CG barree (VO) | Immatriculation, VIN, titulaire, date CG, puissance fiscale |
| Facture | Vendeur, acheteur, VIN, montant, date, TVA |
| Justificatif domicile | Nom, adresse, date emission, type (energie, impot, loyer) |
| Kbis | Raison sociale, SIRET, siege social, representant legal, date |

### 7.3 Estimation des taxes

Le calculateur estime les composantes de la taxe d'immatriculation :

| Composante | Calcul | Exemple (7 CV, Paris, 130 g/km CO2) |
|------------|--------|--------------------------------------|
| **Y1** — Taxe regionale | Puissance CV x tarif departement | 7 x 46,15 = 323,05 EUR |
| **Y3** — Malus CO2 (WLTP) | Bareme progressif 2026 | 170 EUR |
| **Y4** — Taxe de gestion | 11 EUR fixe (0 si electrique) | 11 EUR |
| **Y5** — Redevance acheminement | 2,76 EUR fixe | 2,76 EUR |
| **Y6** — Malus au poids | 10 EUR/kg > 1 800 kg | 0 EUR |
| **Total estime** | | **506,81 EUR** |

Le tarif regional par CV varie selon le departement (43 EUR/CV par defaut). L'estimation est **indicative et non contractuelle** — le montant final est confirme par le SIV a la soumission.

### 7.4 Mode batch

Pour les professionnels a volume (concessionnaires), Imatra offre un mode batch :

- **Creation en lot** — Jusqu'a 50 dossiers en un seul appel
- **Traitement parallele** — Phase 0 + Phase 1 executees simultanement sur tous les dossiers
- **Tableau recapitulatif** — Vue d'ensemble avec le diagnostic par dossier
- **GO groupe** — Selection des dossiers VERT et lancement en lot
- **Pre-autorisation groupee** — Montant = honoraires x nombre de dossiers lances
- **Debit uniquement sur les dossiers aboutis** (CPI genere)

### 7.5 Relances automatiques

Quand un dossier est ROUGE ou en attente client, le systeme gere les relances :

| Parametre | Options |
|-----------|---------|
| Mode | "Me relancer" (notification au pro) / "Relancer le client directement" (SMS auto) |
| Frequence | J+1, J+3, J+7 (configurable par le pro) |
| Contenu | Liste precise des pieces manquantes et corrections requises |
| Escalade | Automatique apres N relances sans reponse |

---

## 8. Parcours utilisateurs

### 8.1 Parcours pro — Dossier classique

```
1. CONNEXION
   Le pro se connecte a son dashboard Imatra

2. CREATION DOSSIER
   → Nouveau dossier (VN ou VO, detection auto)
   → Message d'accueil contextuel :

   "Vehicule neuf : deposez le COC et la facture de vente.
    Vehicule d'occasion : deposez la carte grise barree si vous l'avez.
    Les documents client peuvent etre deposes par vous
    ou par le client via un lien SMS."

3. DEPOT DOCUMENTS VEHICULE
   → Le pro uploade COC + facture (VN) ou CG barree (VO)
   → Classification et extraction automatiques
   → Checklist mise a jour en temps reel
   → Verrou vehicule : deverrouille quand type detecte + docs OK

4. ENVOI LIEN CLIENT (optionnel)
   → Si le pro n'a pas les docs client, il envoie un lien SMS
   → Le client recoit un lien securise avec token temporaire
   → Le client uploade ses documents (CNI, permis, domicile)
   → Le pro voit la progression en temps reel

5. DIAGNOSTIC
   → VERT : dossier pret
   → ORANGE : verifier les avertissements
   → ROUGE : corriger les blocages (liste precise)

6. GENERATION CERFA
   → Cerfa pre-rempli automatiquement (13749 VN ou 13750 VO)
   → Cachet et signature du pro apposes automatiquement
   → PDF pret a telecharger

7. SOUMISSION (SaaS : le pro soumet lui-meme / Full Service : Imatra soumet)
```

### 8.2 Parcours client via SMS

```
1. RECEPTION SMS
   "Bonjour, [NOM_COMMERCE] prepare votre carte grise.
    Merci de deposer vos documents ici : [LIEN]"

2. PAGE CLIENT MOBILE
   → Interface simple, mobile-first
   → Checklist claire des documents attendus
   → Upload par photo (camera) ou fichier

3. ALERTES TEMPS REEL
   → CNI expiree : message d'alerte
   → Domicile > 6 mois : message d'alerte
   → Nom divergent : notification au pro

4. VERIFICATION
   → Chaque document uploade est verifie instantanement
   → Le client voit le statut (OK / probleme) en temps reel

5. CONFIRMATION
   → Tous les documents OK → message de confirmation
   → Le pro est notifie que le dossier client est complet
```

### 8.3 Parcours client-initie (URL permanente)

```
1. ACCES URL
   → Le client accede a imatra.fr/nom-commerce
   → Page publique avec informations du commerce

2. FORMULAIRE
   → Le client entre : nom, prenom, telephone
   → Il depose ses documents (identite, permis, domicile)

3. CREATION DOSSIER
   → Un dossier est cree automatiquement dans l'espace pro
   → Statut : "Nouveau — initie par le client"

4. PRISE EN CHARGE PRO
   → Le pro est notifie
   → Il prend le relais (docs vehicule, verification, Cerfa)
```

### 8.4 Parcours vendeur non habilite + agent

```
1. VENDEUR : cree le dossier, depose les docs vehicule
2. VENDEUR : active "demande d'envoi de mandat" a son agent
3. AGENT : recoit la demande (envoi auto ou manuel selon config)
4. AGENT : genere le mandat client→agent (Cerfa 13757)
         + signature automatique de l'agent (enregistree a l'inscription)
5. VENDEUR : envoie le lien SMS au client
6. CLIENT : uploade ses documents + signe les 2 mandats par OTP SMS
7. VENDEUR ET AGENT : recoivent simultanement les mandats signes + dossier complet
8. AGENT : controle la conformite → telecharge le ZIP → soumet au SIV
```

### 8.5 Scan mobile QR

Pour les situations ou le pro est en face du client (livraison vehicule, etc.) :

```
1. Le pro genere un QR code temporaire (token 8 caracteres, valide 10 min)
2. Le client scanne avec son telephone
3. Page mobile avec capture camera
4. Le document uploade rejoint le dossier en temps reel
5. Le pro voit l'update sur son desktop instantanement
```

---

## 9. Generation Cerfa automatisee

### 9.1 Cerfa pris en charge

| Cerfa | Numero | Usage |
|-------|--------|-------|
| **Demande d'immatriculation VN** | 13749 | Vehicule neuf |
| **Demande d'immatriculation VO** | 13750 | Vehicule d'occasion |
| **Certificat de cession** | 15776 | Transfert de propriete |
| **Mandat** | 13757 | Delegation a un tiers (agent habilite) |

### 9.2 Methode de generation

La generation des Cerfa est 100% **PIL (Python Imaging Library)**, sans dependance navigateur :

1. **Image vierge** — Le Cerfa officiel est stocke comme image de reference (200 DPI, 1654x2339 px)
2. **Annotation pixel** — Chaque champ a des coordonnees pixel precises, validees visuellement
3. **Remplissage** — Les donnees extraites sont inscrites aux positions exactes avec les polices appropriees :
   - Police standard : 17 px
   - Police grande : 19 px
   - Police extra-large : 22 px
   - Police cachet : 12 px
4. **Cases a cocher** — Marques "✓" aux positions pixel exactes (couleur, usage, type personne, sexe, etc.)
5. **Cachet + signature** — Le cachet du pro (nom, adresse, SIRET) et sa signature numerisee sont apposes automatiquement
6. **Export PDF** — L'image annotee est convertie en PDF

### 9.3 Champs remplis automatiquement

Pour le Cerfa VN (13749) par exemple :
- Cases constructeur/representant
- Identification vehicule (D.1, D.2, D.2.1, E)
- Masses (F.1, F.2, F.3, G, G.1)
- Categorie et carrosserie (J, J.1, J.2, J.3)
- Puissance et energie (P.1, P.2, P.3, P.6)
- Places (S.1, S.2)
- Sonore, CO2, environnement (U.1, U.2, V.7, V.9)
- Usage, couleur (cases a cocher)
- Identite demandeur (nom, date naissance, lieu naissance, adresse)
- Co-titulaire si applicable
- Certificat de vente (date, cachet, signature)

Le pro n'a **rien a remplir manuellement**. Le Cerfa sort pret a imprimer et signer.

---

## 10. Conformite reglementaire et RGPD

### 10.1 Cadre juridique d'Imatra

Imatra est un **prestataire technique** au service du professionnel habilite SIV. Il ne se substitue pas au professionnel et ne porte pas la responsabilite des dossiers soumis. Le professionnel reste le seul responsable legal de chaque soumission au SIV.

Ce positionnement est conforme a la convention d'habilitation SIV qui autorise le recours a des outils techniques pour la preparation des dossiers, tant que le professionnel habilite conserve la maitrise et la responsabilite de la verification et de la soumission.

### 10.2 Cibles juridiquement validees

| Cible | Statut | Commentaire |
|-------|--------|-------------|
| Vendeurs pro habilites SIV | **OK** | Cible principale — outil technique autorise |
| Mandataires habilites SIV | **OK** | Meme cadre que vendeur habilite |
| Agents habilites SIV | **OK** | Pour leurs propres clients |
| Points carte grise habilites (tabacs, etc.) | **OK** | Meme cadre |
| Vendeurs non habilites + agent partenaire | **Zone grise** | Faisable si l'agent a son propre compte. Avis avocat recommande |
| Points CG physiques / franchises | **Exclus** | Hors cible marketing |
| Plateformes en ligne | **Exclus** | CGV + filtre NAF |

### 10.3 RGPD — Protection des donnees

#### Base legale

| Partie | Base legale | Justification |
|--------|-------------|---------------|
| Professionnel | Contrat (art. 6.1.b RGPD) | Execution du service souscrit |
| Client du pro | Consentement explicite (art. 6.1.a RGPD) | Checkbox + consentement date et horodate |

#### Sous-traitants

| Sous-traitant | Service | Localisation | Protection |
|---------------|---------|-------------|------------|
| Google LLC | Document AI (OCR) | US (traitement EU) | SCCs (art. 46 RGPD) |
| Anthropic | Claude (IA extraction) | US | SCCs (art. 46 RGPD) |
| AWS | S3 (stockage documents) | eu-west-3 (Paris) | Hebergement UE |
| Neon | PostgreSQL | eu-central-1 (Francfort) | Hebergement UE |
| Stripe | Paiement | US | SCCs |
| Twilio | SMS | US | SCCs |

#### Durees de conservation

| Donnee | Duree | Base legale |
|--------|-------|-------------|
| Documents uploades (CNI, permis, etc.) | **Supprimes a la finalisation du Cerfa** | Minimisation (art. 5.1.c RGPD) |
| Donnees personnelles client (prenom, tel, email) | **Supprimes a la finalisation** | Minimisation |
| Nom titulaire (pour archivage dossier) | **5 ans** | Obligation legale (archivage CG) |
| Donnees de facturation | **10 ans** | Obligation comptable |
| Dossier finalise (metadonnees) | **5 ans** | Obligation legale |

#### Cleanup RGPD automatique

Le moteur RGPD supprime automatiquement apres generation du Cerfa :
- Tous les fichiers documents (S3)
- Prenom, telephone et email du client
- Seul le nom du titulaire est conserve (obligation legale 5 ans)

### 10.4 Conditions Generales de Vente

Les CGV d'Imatra incluent :
- 14 articles couvrant l'ensemble du service
- Clause `cgv_acceptees` obligatoire avant toute utilisation
- **Clause anti-concurrence** : les plateformes en ligne de carte grise sont exclues du service
- Modalites de l'essai : 5 dossiers sans avance de frais, factures si continuation
- Le tarif est independant du prix facture par le pro a son client

---

## 11. Modele economique

### 11.1 Tarification simple et transparente

| Element | Tarif |
|---------|-------|
| Dossier voiture | **14 EUR** |
| Dossier moto | **12 EUR** |
| Phase 0 + Phase 1 (OCR, diagnostic) | **Absorbe** par la plateforme |
| Essai | **5 dossiers sans avance de frais** |

Le tarif est **fixe et independant du prix facture par le pro a son client**. Imatra ne prend pas de commission sur le service du professionnel.

### 11.2 Flux de paiement

```
Depot documents → Phase 0 + Phase 1 (gratuit)
    → Diagnostic VERT
    → Pre-autorisation CB (12 ou 14 EUR)
    → Generation Cerfa + CPI
    → Debit effectif uniquement si CPI genere
```

**Principe cle** : le pro ne paie que si le dossier aboutit. Pas de CPI genere = pas de debit.

### 11.3 Options de facturation

| Mode | Description | Cible |
|------|-------------|-------|
| **Unitaire** | Pre-autorisation CB par dossier, debit sur CPI | Petits volumes |
| **Abonnement** | 50-150 EUR/mois + tarif reduit par dossier | Volumes reguliers |
| **SEPA** | Facture mensuelle + prelevement | Gros volumes |

### 11.4 Gardes-fous facturation

- **Essai gratuit** : 5 premiers dossiers sans avance de frais (ESSAI_GRATUIT = 5)
- **Batch max** : maximum 5 dossiers en statut CERFA_GENERE sans paiement capture (BATCH_MAX = 5). Au-dela, le pro doit regulariser avant de continuer.

### 11.5 Separation honoraires / taxes

Le systeme distingue clairement deux flux financiers :

| Flux | Quoi | A qui | Comment |
|------|------|-------|---------|
| **Honoraires** | Remuneration Imatra | A Imatra | Stripe (pre-auth → debit sur CPI) |
| **Taxes SIV** | Taxes d'immatriculation (Y1+Y3+Y4+Y5+Y6) | A l'Etat | Payees par le pro dans le SIV |

Imatra ne collecte pas les taxes pour le compte de l'Etat. Le pro les paie directement dans le formulaire SIV.

### 11.6 Projections financieres

| Hypothese | An 1 | An 2 | An 3 |
|-----------|------|------|------|
| Pros actifs | 10 - 20 | 80 - 150 | 300 - 500 |
| Dossiers / pro / mois | 5 - 10 | 10 - 15 | 15 - 20 |
| Dossiers / mois | 100 - 200 | 1 000 - 2 000 | 5 000 - 10 000 |
| CA mensuel | 3 000 - 8 000 EUR | 30 000 - 70 000 EUR | 150 000 - 300 000 EUR |
| Marge brute | ~80% | ~85% | ~88% |

La marge brute elevee s'explique par :
- Cout OCR Phase 1 absorbe (~0,50 EUR par dossier)
- Pas de cout humain en regime permanent (tout est automatise)
- Infrastructure cloud a cout variable (pas de serveur dedie)

---

## 12. Positionnement concurrentiel

### 12.1 Panorama concurrentiel

| Acteur | Type | Ce qu'il fait | Ce qu'il ne fait pas |
|--------|------|---------------|---------------------|
| **AutoCerfa / Centre SIV** | Logiciel SIV | Pre-remplissage depuis saisie manuelle + soumission SIV | Pas d'OCR, pas de verification automatique, pas de collecte client |
| **Plateformes en ligne** (Eplaque, Cartegrise.com, etc.) | B2C | Service complet pour particuliers | Ne s'adressent pas aux pros en B2B |
| **DMS (logiciels garage)** | ERP garage | Gestion vehicules, factures, atelier | Pas de traitement CG avance |
| **Imatra** | **SaaS B2B** | **OCR + IA + 200 controles + collecte client SMS + Cerfa auto** | Ne soumet pas au SIV (en mode SaaS) |

### 12.2 Avantage differentiel

Imatra se positionne comme **complementaire** aux logiciels SIV existants, pas concurrent :

| Critere | Logiciel SIV classique | Imatra |
|---------|----------------------|-------------|
| Saisie des donnees | Manuelle (le pro tape tout) | Automatique (OCR + extraction) |
| Verification conformite | Aucune (verification humaine) | 38 regles + 21 croisements temps reel |
| Collecte documents client | Hors perimetre | Lien SMS + upload mobile |
| Temps pro par dossier | 30-45 min | < 5 min |
| Detection d'erreurs | A la soumission (rejet SIV) | Avant soumission (diagnostic) |
| Generation Cerfa | Manuelle | Automatique (100% pre-rempli) |

### 12.3 Chiffres comparatifs

| Metrique | Methode actuelle | Avec Imatra |
|----------|-----------------|------------------|
| Temps par dossier | 30-45 min | < 5 min |
| Taux de rejet SIV | 15-25% | < 2% (objectif) |
| Delai verification | 12-24h (manuelle) | Temps reel |
| Delai reponse client | ~42h (moyenne secteur) | Immediat (SMS) |
| Relances manuelles | Appels telephoniques | Automatiques (SMS/email) |

---

## 13. Securite et gardes-fous

### 13.1 Authentification et acces

| Couche | Methode |
|--------|---------|
| Authentification pro | JWT (HS256, expiration 60 min) |
| Acces client | Token securise temporaire (lien SMS) |
| Scan mobile | Token 8 caracteres, expire apres 10 min |
| Rate limiting | 60 requetes/minute par IP |

### 13.2 Filtre NAF (legitimite commerciale)

Avant toute inscription, Imatra verifie le code NAF de l'entreprise via l'API Recherche Entreprises (gratuite, sans cle) :

**Codes autorises** (15 activites automobiles legitimes) :
- 45.11Z (vente automobiles), 45.20A/B (reparation), 45.31Z/32Z (pieces auto)
- 77.11A/B (location vehicules), 70.22Z (conseil gestion), etc.

**Codes interdits** (activites concurrentes / mandataires en ligne) :
- 82.99Z (services de soutien), 82.11Z (services administratifs)
- 62.01Z (programmation informatique), 63.12Z (portails internet)

**Detection supplementaire** : 10 mots-cles suspects dans le nom de l'entreprise (carte grise, immatriculation, mandataire, eplaque, etc.)

**Resultats** : `ok` / `refuse` / `alerte` / `introuvable`

### 13.3 Controle de volume

| Seuil | Dossiers/mois | Action |
|-------|---------------|--------|
| Normal | ≤ 50 | Aucune restriction |
| Alerte | 50 - 100 | Monitoring, notification interne |
| Blocage | > 100 | Investigation obligatoire (activite de mandataire en ligne detectee) |

Un rapport de surveillance mensuel recense les anomalies de volume.

### 13.4 Chiffrement et stockage

| Donnee | Protection |
|--------|------------|
| Documents S3 | SSE-AES256 (chiffrement au repos) |
| Transit | TLS 1.2+ (chiffrement en transit) |
| Mots de passe | Hachage bcrypt |
| Tokens JWT | HS256 signe |
| Fichiers hash | SHA-256 (deduplication + integrite) |

### 13.5 3 niveaux de verification identite

| Niveau | Qui | Quand | Methode |
|--------|-----|-------|---------|
| NIV.1 | Le pro | A la vente (en personne) | Verification physique CNI originale |
| NIV.2 | Le systeme | Automatique, 100% des dossiers | OCR + croisements + KYC anti-fraude |
| NIV.3 | L'operateur | Si KYC = SUSPECT (~10%) | Controle visuel document vs photo |

---

## 14. Roadmap

### Q1 2026 — Moteur + API (fait)

- [x] 38 regles de verrouillage implementees et testees
- [x] 21 regles de croisement implementees et testees
- [x] Pipeline Phase 0 (HistoVec) et Phase 1 (pre-qualification)
- [x] Diagnostic tri-couleur VERT/ORANGE/ROUGE
- [x] API REST complete (dossiers, documents, decisions, batch)
- [x] Classification et extraction OCR
- [x] Estimation des taxes (Y1, Y3-Y6)
- [x] Generation Cerfa pre-remplis (VN 13749, VO 13750) — 100% PIL
- [x] Separation paiement honoraires / taxes SIV
- [x] Moteur de relances automatiques
- [x] Mode batch (creation + lancement + statut groupe)
- [x] Logique personne morale (detection auto, adaptation regles)
- [x] Endpoint SIV payload
- [x] 3 profils pro (vendeur habilite, vendeur non habilite, agent habilite)
- [x] URL permanente par pro (slug + page publique)
- [x] Parcours client via SMS + page client mobile
- [x] Dashboard React + TypeScript + Vite + Tailwind
- [x] Site commercial (3 pages profils + pages legales + demos)

### Q2 2026 — OCR production + Deploiement

- [ ] Cablage Google Document AI en production
- [ ] Portail React complet (remplacement prototype)
- [ ] Authentification JWT + RBAC
- [ ] Integration Stripe (pre-autorisation, debit, SEPA)
- [ ] Envoi SMS reel (Twilio)
- [ ] Alembic migrations + deploiement staging (Railway/Render)
- [ ] Migration site commercial vers WordPress (Hostinger)

### Q3 2026 — KYC + Habilitation SIV

- [ ] Integration KYC (Ariadnext ou IDnow)
- [ ] Obtention habilitation SIV
- [ ] Acces au formulaire SIV reel
- [ ] Generation mandats Cerfa 13757 (flux vendeur non habilite)
- [ ] Partage dossier entre vendeur non habilite et agent habilite
- [ ] Signature numerique cession (OTP SMS)
- [ ] Beta avec 5-10 garages pilotes

### Q4 2026 — Lancement commercial

- [ ] Extension navigateur SIV (pre-remplissage automatique)
- [ ] Livraison dossier SaaS validee
- [ ] Coffre-fort numerique certifie (archivage 5 ans)
- [ ] Lancement commercial (objectif : 10-20 pros actifs)
- [ ] Integration DMS (connecteurs logiciels garage)

### 2027 — Scale

- [ ] Objectif 80-150 pros actifs
- [ ] API publique pour integrations tierces
- [ ] Extension a d'autres operations SIV (changement adresse, duplicata)
- [ ] Multi-sites (un pro, plusieurs etablissements)

---

## 15. Metriques du projet

| Metrique | Valeur |
|----------|--------|
| Modules Python (moteur + API) | ~60 |
| Lignes de code | ~8 500+ |
| Regles de verrouillage (V-XX) | 38 |
| Regles de croisement (C-XX) | 21 |
| Types de documents geres | 31 |
| Scenarios couverts (S-XX) | 20 |
| Endpoints API | 18+ |
| Profils professionnels | 3 |
| Cerfa generes automatiquement | 4 (13749, 13750, 15776, 13757) |
| Integrations externes | 8 (Google DocAI, Claude, Stripe, Twilio, INSEE, BAN, HistoVec, NHTSA) |

---

## 16. Annexes

### Annexe A — Les 20 scenarios couverts

#### Cas acheteur

| Code | Scenario | Niveau |
|------|----------|--------|
| S-01 | Acheteur societe (personne morale) | Semi-auto |
| S-02 | Co-titulaires maries / pacses | Semi-auto |
| S-03 | Co-titulaires non maries | Semi-auto |
| S-04 | Acheteur mineur | Escalade humaine |
| S-05 | Acheteur etranger resident | Semi-auto |
| S-06 | Acheteur heberge (pack 4 docs) | Semi-auto |
| S-07 | Acheteur sous tutelle / curatelle | Escalade humaine |

#### Cas vehicule (VO)

| Code | Scenario | Niveau |
|------|----------|--------|
| S-08 | CG avec adresse non mise a jour | Semi-auto |
| S-09 | CG perdue | Escalade humaine |
| S-10 | CG au nom d'un defunt | Escalade humaine |
| S-11 | Vehicule gage | Escalade humaine |
| S-12 | Vehicule sous OTCI | Escalade humaine |
| S-13 | Vehicule VEC / VEI | Escalade humaine |
| S-14 | Vehicule ancien FNI | Semi-auto |
| S-15 | Erreur sur ancienne CG | Escalade humaine |
| S-16 | Double cession (sans CG intermediaire) | Escalade humaine |

#### Cas VN speciaux

| Code | Scenario | Niveau |
|------|----------|--------|
| S-17 | VN importe UE (quitus fiscal) | Escalade humaine |
| S-18 | VN importe hors UE (846A douane) | Escalade humaine |
| S-19 | Moto transformee (RTI) | Escalade humaine |
| S-20 | VN demo / vehicule de direction | Semi-auto |

### Annexe B — Composantes taxes d'immatriculation

| Composante | Description | Calcul |
|------------|-------------|--------|
| Y1 | Taxe regionale | Puissance fiscale x tarif CV du departement |
| Y3 | Malus CO2 (WLTP) | Bareme progressif (seuil 2026) |
| Y4 | Taxe de gestion | 11 EUR fixe (0 pour vehicules electriques) |
| Y5 | Redevance acheminement | 2,76 EUR fixe |
| Y6 | Malus au poids | 10 EUR/kg au-dessus de 1 800 kg |

### Annexe C — Points ouverts

| # | Sujet | Impact | Bloque quoi | Statut |
|---|-------|--------|-------------|--------|
| 1 | Paiement taxes SIV sans agrement Tresor Public | HAUT | Derniere etape Full Service uniquement | Mail envoye a l'ANTS |
| 2 | Extension navigateur — protections anti-bot sur le site SIV | MOYEN | Extension (pas le portail ni Phase 1) | A tester apres habilitation |
| 3 | Avis juridique vendeur non habilite + agent | MOYEN | Lancement offre tripartite | Recommande avant mise en marche |

---

*Imatra — Automatiser l'administratif pour que les professionnels de l'automobile se concentrent sur leur metier.*

*Version 3.0 — Avril 2026*
*Document confidentiel — Ne pas diffuser sans autorisation.*
