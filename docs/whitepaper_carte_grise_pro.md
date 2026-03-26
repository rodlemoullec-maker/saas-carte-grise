# Carte Grise Pro — Whitepaper Technique & Business

**Plateforme B2B d'automatisation des demandes d'immatriculation**
*Version 2.0 — Mars 2026*

---

## 1. Executive Summary

Carte Grise Pro est une plateforme SaaS B2B qui automatise de bout en bout les demandes de carte grise (certificat d'immatriculation) pour les professionnels de l'automobile : garages, concessionnaires, revendeurs motos et voitures.

Le marche francais compte plus de **40 000 garages et revendeurs** qui traitent chacun entre 50 et 500 demandes de carte grise par an. Chaque dossier mobilise en moyenne **30 a 45 minutes** de travail administratif manuel : collecte de documents, verification de conformite, remplissage de formulaires, soumission SIV, suivi.

Carte Grise Pro reduit ce temps a **moins de 5 minutes** par dossier grace a un moteur d'automatisation qui enchaine OCR, extraction structuree, 38 regles de verrouillage, 21 croisements inter-documents, diagnostic binaire VERT/ORANGE/ROUGE, estimation des taxes et generation de Cerfa pre-remplis.

**Deux offres complementaires** :
- **Full Service** — pour les pros non habilites SIV : on gere tout, de la verification a la soumission.
- **SaaS** — pour les pros deja habilites SIV : on prepare un dossier pret a soumettre.

---

## 2. Le Probleme

### 2.1 Complexite reglementaire

Une demande de carte grise implique :
- **31 types de documents** differents selon le cas (vehicule neuf/occasion, acheteur particulier/societe/mineur/etranger)
- **21 regles de coherence croisee** entre documents (identite, VIN, adresse, dates, signatures, statut SIV)
- **38 criteres de verrouillage** qui peuvent bloquer un dossier
- **20 scenarios** de cas d'usage distincts, chacun avec ses specificites documentaires

### 2.2 Erreurs et rejets

Les rejets SIV representent entre **15% et 25%** des soumissions selon les sources professionnelles. Chaque rejet signifie :
- Temps perdu (20-40 min pour diagnostiquer + corriger + resoumettre)
- Client mecontent (delai supplementaire)
- Cout non recuperable pour le pro

### 2.3 Risques de fraude

Le SIV traite plus de 10 millions d'operations par an. Les risques identitaires (faux documents, vehicules voles, gages non declares) necessitent une vigilance que le controle humain seul ne peut pas garantir a grande echelle.

---

## 3. Architecture de la Solution

### 3.1 Vue d'ensemble

```
Pro (Dashboard Web / API)
        |
        v
   FastAPI REST API
   /dossiers  /dossiers/batch  /documents  /decisions  /webhooks
        |
        v (Redis queue)
   Celery Pipeline Worker
        |
   +---------+---------+---------+---------+
   | PHASE 0 | PHASE 1 | PHASE 2 | ARCHIV  |
   | HistoVec| Pre-qual| KYC+SIV | Coffre  |
   +---------+---------+---------+---------+
        |
        v
   PostgreSQL + S3 (documents) + Redis (cache)
```

### 3.2 Les 4 phases du traitement

| Phase | Contenu | Cout | Qui paie |
|-------|---------|------|----------|
| **Phase 0** | Consultation HistoVec/CSA — detection gage, OTCI, vol, VEC/VEI | Gratuit | Absorbe |
| **Phase 1** | Completude + OCR + validation + croisements + diagnostic + estimation taxes | ~0.50 EUR | Absorbe |
| **GO/NO-GO** | Le pro voit le diagnostic VERT/ORANGE/ROUGE et decide de lancer le traitement | 0 EUR | — |
| **Phase 2** | KYC anti-fraude + soumission SIV (Full Service) ou livraison dossier (SaaS) | 1-3 EUR | Honoraires pro |

### 3.3 Diagnostic tri-couleur

Un dossier carte grise est conforme ou il ne l'est pas. Il n'y a pas de "75% bon". Le moteur produit un diagnostic binaire :

- **VERT** — Zero verrouillage V-XX, zero warning. Le dossier est complet et conforme. Le pro peut lancer le traitement en un clic.
- **ORANGE** — Zero verrouillage, mais au moins un avertissement non bloquant (CT bientot expire, OCR moyen, assurance provisoire < 7 jours). Le pro peut continuer apres verification.
- **ROUGE** — Au moins un verrouillage V-XX declenche. Le dossier ne peut pas avancer. Le pro voit la liste exacte des blocages avec les actions correctives a mener.

Le pro voit la **liste detaillee des blocages et warnings**, pas un score abstrait. Chaque blocage indique le code V-XX, le document concerne, et l'action corrective a mener.

### 3.4 Mode batch

Le pro peut traiter plusieurs dossiers en lot :
- **Upload multiple** — creer jusqu'a 50 dossiers en un seul appel (`POST /dossiers/batch`)
- **Traitement parallele** — Phase 0 + Phase 1 executees en parallele sur tous les dossiers
- **Tableau recapitulatif** — le pro voit le diagnostic VERT/ORANGE/ROUGE par dossier
- **GO groupe** — le pro selectionne les dossiers VERT et lance le traitement en lot (`POST /dossiers/batch/launch`)
- **Pre-autorisation CB groupee** — montant = honoraires x nombre de dossiers lances
- **Debit uniquement sur les dossiers aboutis** (CPI genere)

### 3.5 Relances automatiques

Quand un dossier est ROUGE, le systeme declenche des relances automatiques :
- Le pro configure dans son portail : **"me relancer"** ou **"relancer directement mon client"**
- Frequence configurable : J+1, J+3, J+7 (defaut)
- Escalade automatique si pas de reponse apres N relances
- Chaque relance precise les pieces manquantes et corrections requises

---

## 4. Moteur de Regles

### 4.1 Referentiel documentaire (31 documents)

Le systeme connait 31 types de documents, chacun avec ses regles de validite, ses champs a extraire et ses controles specifiques :

| Categorie | Documents | Exemples |
|-----------|-----------|----------|
| Formulaires | D-01 a D-06 | Cerfa 13749 (VN), 13750 (VO), 15776 (cession), 13757 (mandat), DA |
| Identite acheteur | D-07 a D-10 | CNI, passeport, titre de sejour, permis de conduire |
| Justificatif domicile | D-11 a D-15 | Facture energie, avis imposition, quittance loyer, pack hebergement |
| Vehicule | D-16 a D-22 | COC, CG barree, CT, assurance, code cession, recepisse DA, HistoVec |
| Personne morale | D-23 a D-25 | Kbis, CNI representant legal, statuts/PV AG |
| Cas speciaux | D-26 a D-31 | Livret famille, autorisation parentale, tutelle, deces, mainlevee gage, attestation pro |

### 4.2 Regles de coherence croisee (21 regles C-XX)

Chaque regle compare des donnees extraites de documents differents :

**Identite (C-01 a C-05)** — Fuzzy matching des noms entre CNI, Cerfa, permis, assurance, domicile. Seuils : >= 97% auto, 85-96% warning, < 85% blocage.

**Vehicule (C-06 a C-10)** — VIN identique sur tous les documents. CNIT vs base UTAC. Puissance fiscale +-1CV warning / +-3CV blocage. CO2 WLTP obligatoire post-2021.

**Chaine de propriete VO (C-11 a C-14)** — Vendeur DA = titulaire CG. Chronologie dates CG/DA/cession. Signatures co-titulaires. CT valide a la saisie SIV.

**Permis et age (C-15, C-16)** — Categorie permis vs type vehicule. Age vs categorie autorisee (< 14 : rien, 14-15 : AM, 16-17 : A1, >= 18 : B).

**Statut SIV (C-17 a C-21)** — Gage, OTCI, VEC/VEI, vol signale, doublon VIN interne.

### 4.3 Criteres de verrouillage (38 regles V-XX)

Chaque V-XX declenche un **blocage ROUGE** si non satisfait :

| Categorie | Regles | Exemples |
|-----------|--------|----------|
| Documents manquants | V-01 a V-10, V-36 | CNI absente, permis absent, COC absent, DA absente |
| Validite temporelle | V-11 a V-19 | CNI expiree, permis expire, CT > 6 mois, Kbis > 3 mois |
| Qualite documentaire | V-20 a V-23 | Score OCR < 40%, scan tronque, langue etrangere, rature Cerfa |
| Coherence | V-24 a V-28 | VIN incoherent, identite incoherente, chaine propriete brisee |
| Statut SIV | V-29 a V-32 | Gage actif, OTCI, VEC/VEI, vol signale |
| Controles specifiques | V-33 a V-38 | CG non barree, signature manquante, CT defavorable, KYC echec |

### 4.4 Personne morale (PM)

Quand l'acheteur est une personne morale, le moteur adapte son comportement :
- **Permis** : non exige (exception a V-02). Seul le titulaire principal personne physique doit avoir un permis.
- **Justificatif de domicile** : remplace par le Kbis. L'adresse sur la CG = adresse du siege social.
- **CNI** : celle du representant legal (gerant/president sur le Kbis), pas du "client".
- **Coherence nom** : le Cerfa mentionne la raison sociale du Kbis, pas le nom du gerant.
- **Kbis** : doit etre de moins de 3 mois (V-15).
- **Detection auto** : presence d'un Kbis dans les docs ou SIREN/SIRET dans le Cerfa.

---

## 5. Pipeline Technique

### 5.1 OCR et extraction structuree

1. **Upload** — Le pro uploade un document (PDF, JPG, PNG). Le systeme calcule le SHA-256 et stocke le fichier.
2. **Classification automatique** — Un classifieur par mots-cles ponderes identifie le type parmi 17 categories. Si confiance < 60%, le pro est invite a preciser manuellement.
3. **OCR** — Google Document AI extrait le texte brut avec un **score de confiance OCR par document** (conserve pour evaluer la lisibilite, V-20).
4. **Extraction structuree** — Des regex metier specialisees par type de document extraient les champs structures (VIN, dates, noms, montants, etc.).
5. **Fallback LLM** — Pour les documents complexes ou mal structures, un LLM (Claude) extrait les donnees en mode conversationnel.

### 5.2 Estimation des taxes

Le calculateur estime les composantes de la taxe d'immatriculation :

| Composante | Calcul | Exemple (7 CV, Paris, 130 g/km CO2) |
|------------|--------|--------------------------------------|
| Y1 — Taxe regionale | Puissance CV x tarif departement | 7 x 46.15 = 323.05 EUR |
| Y3 — Malus CO2 (WLTP) | Bareme progressif 2026 | 170 EUR |
| Y4 — Taxe de gestion | 11 EUR fixe (0 si electrique) | 11 EUR |
| Y5 — Redevance acheminement | 2.76 EUR fixe | 2.76 EUR |
| Y6 — Malus au poids | 10 EUR/kg > 1800 kg | 0 EUR |
| **Total estime** | | **506.81 EUR** |

*Note : montant final confirme par le SIV a la soumission. L'estimation est indicative et non contractuelle.*

### 5.3 3 niveaux d'authentification identite

| Niveau | Qui | Quand | Methode |
|--------|-----|-------|---------|
| NIV.1 | Le pro | A la vente (en personne) | Verification physique CNI originale + attestation dans le portail |
| NIV.2 | Le systeme | Automatique, 100% des dossiers | OCR + croisements + KYC anti-fraude (Ariadnext / IDnow) |
| NIV.3 | L'operateur | Uniquement si KYC = SUSPECT (~10%) | Controle visuel document vs photo, ~10 min |

### 5.4 Endpoint SIV Payload

L'endpoint `GET /dossiers/{id}/siv-payload` retourne toutes les donnees du dossier formatees pour le formulaire SIV (dans l'ordre des champs). Ce payload sert a :
- **L'extension navigateur** — pre-remplissage automatique des champs SIV
- **Le recapitulatif copier-coller** — fallback si l'extension est indisponible
- **La livraison dossier SaaS** — donnees structurees pour le pro habilite

---

## 6. Modele Economique

### 6.1 Separation honoraires / taxes

Le systeme de paiement distingue clairement deux flux :

| Flux | Quoi | A qui | Comment | Statut |
|------|------|-------|---------|--------|
| **Honoraires** | Remuneration du porteur de projet (30-60 EUR FS, 10-25 EUR SaaS) | Au porteur | Stripe/PayPlug : pre-auth CB au GO, debit sur CPI genere | Pret a developper |
| **Taxes SIV** | Taxes d'immatriculation (Y1+Y3+Y4+Y5+Y6) | A l'Etat | Payees par CB dans le formulaire web SIV | **En attente reponse ANTS** |

**Point bloquant (Full Service uniquement)** : Le porteur est habilite SIV **sans agrement Tresor Public** (non eligible : pas de commerce de vehicules). Sans agrement, il ne peut pas percevoir les taxes pour le compte de l'Etat. Un mail a ete envoye a l'ANTS (siv-pha@interieur.gouv.fr) pour clarifier le mecanisme de paiement CB dans le formulaire SIV habilite sans agrement.

Ce point ne bloque **ni le SaaS** (le pro paie ses taxes dans son propre SIV), **ni le portail**, **ni la Phase 0/1**, **ni le KYC**.

### 6.2 Offre Full Service

**Cible** : Pros non habilites SIV (la majorite des petits garages).

| Element | Detail |
|---------|--------|
| Cout plateforme par dossier | 2 - 5 EUR |
| Prix au pro (honoraires) | 30 - 60 EUR |
| Marge brute | 25 - 58 EUR |
| Cas complexes (import, deces, tutelle) | 60 - 150 EUR |
| Paiement honoraires | Pre-autorisation CB au GO ; debit sur CPI genere |
| Alternative | Facture mensuelle + prelevement SEPA pour les pros a volume |

### 6.3 Offre SaaS

**Cible** : Pros deja habilites SIV (concessionnaires, mandataires).

| Element | Detail |
|---------|--------|
| Cout plateforme par dossier | 0.70 - 2.50 EUR |
| Prix au pro | 10 - 25 EUR/dossier OU 50 - 150 EUR/mois + tarif reduit |
| Marge brute | 7.50 - 24.30 EUR |
| Livrable | Dossier complet + donnees extraites + KYC + estimation taxes + checklist |
| Pas d'operateur | Le pro soumet lui-meme dans son SIV |

### 6.4 Projection

| Hypothese | An 1 | An 2 | An 3 |
|-----------|------|------|------|
| Pros actifs | 10 - 20 | 80 - 150 | 300 - 500 |
| Dossiers / pro / mois | 5 - 10 | 10 - 15 | 15 - 20 |
| Dossiers / mois | 100 - 200 | 1 000 - 2 000 | 5 000 - 10 000 |
| CA mensuel (mix 60% FS / 40% SaaS) | 3 000 - 8 000 EUR | 30 000 - 70 000 EUR | 150 000 - 300 000 EUR |
| Marge brute | ~80% | ~85% | ~88% |

---

## 7. Les 20 Scenarios Couverts

### Cas acheteur

| Code | Scenario | Niveau |
|------|----------|--------|
| S-01 | Acheteur societe (personne morale) | Semi-auto |
| S-02 | Co-titulaires maries / pacses | Semi-auto |
| S-03 | Co-titulaires non maries | Semi-auto |
| S-04 | Acheteur mineur | Escalade humaine |
| S-05 | Acheteur etranger resident | Semi-auto |
| S-06 | Acheteur heberge (pack 4 docs) | Semi-auto |
| S-07 | Acheteur sous tutelle / curatelle | Escalade humaine |

### Cas vehicule (VO)

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

### Cas VN speciaux

| Code | Scenario | Niveau |
|------|----------|--------|
| S-17 | VN importe UE (quitus fiscal) | Escalade humaine |
| S-18 | VN importe hors UE (846A douane) | Escalade humaine |
| S-19 | Moto transformee (RTI) | Escalade humaine |
| S-20 | VN demo / vehicule de direction | Semi-auto |

---

## 8. Stack Technique

| Composant | Technologie |
|-----------|-------------|
| API | FastAPI (Python 3.11+, async) |
| Workers | Celery + Redis |
| BDD | PostgreSQL (Neon, managed) |
| Stockage documents | AWS S3 (eu-west-3, SSE-AES256) |
| OCR | Google Document AI (EU) |
| LLM fallback | Anthropic Claude |
| KYC | Ariadnext / IDnow |
| Paiement honoraires | Stripe / PayPlug |
| Dashboard | Streamlit (prototype) → React/Next.js (production) |
| CI/CD | GitHub Actions |
| Monitoring | Sentry + Grafana |
| Infrastructure | Docker Compose (dev) / AWS ECS (prod) |

### Conformite

- **RGPD** — Donnees hebergees en France (AWS eu-west-3). Chiffrement au repos et en transit. Purge automatique apres delai legal. Registre des traitements.
- **Archivage 5 ans** — Coffre-fort numerique certifie obligatoire depuis 2026 (arrete du 1er juillet 2025).
- **Habilitation SIV** — Demande en cours de preparation aupres de l'ANTS.

---

## 9. Metriques du Projet

| Metrique | Valeur |
|----------|--------|
| Modules Python (moteur + API) | ~60 |
| Lignes de code | ~8 500 |
| Tests unitaires | 132 (100% pass) |
| Regles de verrouillage (V-XX) | 38 |
| Regles de croisement (C-XX) | 21 |
| Types de documents geres | 31 |
| Scenarios couverts (S-XX) | 20 |
| Endpoints API | 15 (dont 3 batch) |
| Templates email / relance | 7 |

---

## 10. Roadmap

### Phase actuelle (Q1 2026) — Moteur + API

- [x] 38 regles de verrouillage implementees et testees
- [x] 21 regles de croisement implementees et testees
- [x] Pipeline Phase 0 (HistoVec) et Phase 1 (pre-qualification)
- [x] Diagnostic binaire VERT/ORANGE/ROUGE (pas de score pondere)
- [x] API REST complete (dossiers, documents, decisions, batch)
- [x] Classification et extraction OCR
- [x] Estimation des taxes (Y1, Y3-Y6)
- [x] Generation Cerfa pre-remplis
- [x] Separation paiement honoraires / taxes SIV
- [x] Moteur de relances automatiques (PRO/SYSTEME, J+1/3/7)
- [x] Mode batch (creation + lancement + statut groupe)
- [x] Logique personne morale (detection auto, adaptation regles)
- [x] Endpoint SIV payload (extension + copier-coller + SaaS)
- [x] 132 tests unitaires

### Q2 2026 — Portail Pro + OCR reel

- [ ] Cablage Google Document AI (OCR production)
- [ ] Dashboard Streamlit operationnel → portail React/Next.js en parallele
- [ ] Authentification JWT + RBAC + 2FA
- [ ] Integration Stripe (pre-autorisation, debit, facturation SEPA)
- [ ] Alembic migrations + deploiement staging

### Q3 2026 — KYC + Habilitation SIV

- [ ] Integration KYC (Ariadnext ou IDnow)
- [ ] Obtention habilitation SIV
- [ ] Acces au formulaire SIV reel → finalisation extension navigateur
- [ ] Resolution mecanisme paiement taxes (reponse ANTS)
- [ ] Beta avec 5-10 garages pilotes

### Q4 2026 — Lancement commercial

- [ ] Extension navigateur validee (Full Service)
- [ ] Livraison dossier SaaS validee
- [ ] Coffre-fort numerique certifie (Certigna CFN ou equivalent)
- [ ] Lancement commercial (objectif : 10-20 pros actifs)

---

## 11. Points d'interrogation en cours

| # | Sujet | Impact | Bloque quoi | Statut |
|---|-------|--------|-------------|--------|
| 1 | Paiement taxes SIV sans agrement Tresor Public | HAUT | Derniere etape Full Service uniquement | Mail envoye a l'ANTS, en attente |
| 2 | Extension navigateur — protections anti-bot sur le site SIV | MOYEN | Extension (pas le portail ni Phase 1) | A tester apres habilitation |
| 3 | Estimation taxes vs montant exact SIV | BAS | Rien (estimation = indicatif non contractuel) | Resolu par design |

---

*Carte Grise Pro — Automatiser l'administratif pour que les pros se concentrent sur leur metier.*
