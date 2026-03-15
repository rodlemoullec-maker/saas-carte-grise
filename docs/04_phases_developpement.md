# Phases de développement

## Principe

Le développement se fait en **Python pur** (FastAPI, scripts, tests).
**OpenClaw** n'est intégré qu'en Phase 8 pour l'opérationnel :
il orchestre les modules Python développés aux phases précédentes.

```
Phases 1-7 : Développement classique Python
             (modules, tests, dashboard)

Phase 8 :    Intégration OpenClaw
             (les modules deviennent des skills OpenClaw)

Phase 9 :    Mise en production
             (OpenClaw pilote tout de manière autonome)
```


## Vue d'ensemble

| Phase | Contenu | Prérequis | Statut |
|---|---|---|---|
| 1 | Setup projet, dépendances, PostgreSQL, import types mines | Aucun | À faire |
| 2 | OCR (Surya) + Classification (Qwen2.5-VL) + Extraction → JSON | Phase 1 | À faire |
| 3 | Recherche véhicule (types mines + VIN decoder + stock) | Phase 1 | À faire |
| 4 | Calcul taxes + Pré-remplissage CERFA PDF | Phases 2+3 | À faire |
| 5 | Cross-validation inter-documents | Phase 2 | À faire |
| 6 | Réception email + notifications | Phase 2 | À faire |
| 7 | Dashboard Streamlit (validation opérateur) | Phases 4+5 | À faire |
| 8 | Intégration OpenClaw (modules → skills, orchestration) | Phases 1-7 | À faire |
| 9 | Tests complets + mise en production | Tout | À faire |


## Détail par phase

### Phase 1 — Fondations
- [ ] Installer PostgreSQL via Homebrew
- [ ] Créer la base de données `carte_grise`
- [ ] Créer les tables (dossiers, documents, types_mines, vehicules_stock)
- [ ] Télécharger le fichier types mines depuis data.gouv.fr
- [ ] Script d'import CSV → PostgreSQL
- [ ] Installer les dépendances Python (requirements.txt)
- [ ] Vérifier Ollama + télécharger les modèles (qwen2.5vl:7b, qwen2.5:7b)

### Phase 2 — OCR + Classification + Extraction
- [ ] Preprocessing image (OpenCV) : redressement, contraste, débruitage
- [ ] Intégration Surya OCR : image → texte brut
- [ ] Classification IA (Qwen2.5-VL via Ollama) : image → type document
- [ ] Extracteur carte grise : texte OCR → JSON (champs A-Z)
- [ ] Extracteur CNI : texte OCR → JSON (nom, prénom, date naissance...)
- [ ] Extracteur certificat de cession : texte OCR → JSON
- [ ] Extracteur justificatif domicile : texte OCR → JSON
- [ ] Extracteur contrôle technique : texte OCR → JSON
- [ ] Tests sur documents réels

### Phase 3 — Recherche véhicule
- [ ] Décodeur VIN (table WMI → constructeur, année, usine)
- [ ] Requêtes base types mines (CNIT → fiche technique)
- [ ] Gestion base stock interne (CRUD véhicules)
- [ ] Moteur de recherche multi-sources (VIN / immat / CNIT)

### Phase 4 — CERFA + Taxes
- [ ] Calcul taxe régionale Y1 (CV × tarif région)
- [ ] Calcul taxe formation Y3
- [ ] Calcul malus CO2 Y4 (barème annuel)
- [ ] Calcul malus masse Y5
- [ ] Taxe fixe Y6
- [ ] Mapping données → champs AcroForm du CERFA PDF
- [ ] Génération CERFA 13750 pré-rempli (fillpdf)
- [ ] Gestion des cas : moto, remorque, voiture

### Phase 5 — Cross-validation
- [ ] VIN cohérent entre documents
- [ ] Immatriculation cohérente
- [ ] Nom acheteur CNI = nom certificat cession (fuzzy match)
- [ ] Justificatif domicile < 6 mois
- [ ] CNI non expirée
- [ ] Contrôle technique valide (si applicable)
- [ ] Rapport de validation (erreurs / warnings)

### Phase 6 — Email + notifications
- [ ] Connexion IMAP (polling périodique)
- [ ] Extraction pièces jointes
- [ ] Création automatique dossier par email
- [ ] Envoi accusé réception au client
- [ ] Notification si documents manquants

### Phase 7 — Dashboard Streamlit
- [ ] Liste des dossiers (filtrable par statut)
- [ ] Vue détail dossier : documents côte à côte + données extraites
- [ ] Champs éditables pour correction
- [ ] Indicateurs de confiance (vert/orange/rouge)
- [ ] Alertes cross-validation
- [ ] Bouton validation + génération CERFA
- [ ] Téléchargement PDF

### Phase 8 — Intégration OpenClaw (opérationnel)
- [ ] Installer OpenClaw + configurer Ollama comme provider
- [ ] Transformer chaque module Python en skill OpenClaw :
  - [ ] src/classification → skill-classify
  - [ ] src/ocr + src/extraction → skill-ocr + skill-extract
  - [ ] src/vehicle → skill-vehicle
  - [ ] src/taxes → skill-taxes
  - [ ] src/cerfa → skill-cerfa
  - [ ] src/validation → skill-validate
  - [ ] src/email_handler → skill-notify + canal IMAP
- [ ] Configurer le workflow automatique dans OpenClaw
- [ ] Tester le flux complet : email → CERFA sans intervention
- [ ] Configurer les canaux (email, optionnel : WhatsApp/Slack)

### Phase 9 — Production
- [ ] Tests unitaires tous modules
- [ ] Tests d'intégration (pipeline complète via OpenClaw)
- [ ] Tests sur cas réels (motos, voitures, remorques)
- [ ] Gestion des erreurs et edge cases
- [ ] Déploiement final sur Mac Mini
