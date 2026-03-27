# Parcours Systeme Carte Grise — Vendeur Pro & Client

## Vue d'ensemble

Le systeme automatise la demande de carte grise en collectant les documents du vendeur (pro) et du client (acheteur) via deux espaces separes, puis genere le Cerfa officiel pre-rempli.

```
VENDEUR (Pro)                    CLIENT (Acheteur)
    |                                 |
    v                                 v
Espace Vendeur                  Espace Client
(docs vehicule)                 (docs identite)
    |                                 |
    +────────────┬────────────────────+
                 |
                 v
         MOTEUR CARTE GRISE
    (OCR → Classification → Extraction
     → Diagnostic → Generation Cerfa)
                 |
                 v
          ESPACE ADMIN
    (tous les docs + Cerfa + alertes)
```

---

## 1. Parcours Vendeur (Pro)

Le vendeur est le commercant moto/auto qui vend le vehicule au client.

### Etape 1 : Creation du dossier
Le vendeur cree un nouveau dossier dans son espace admin :
- Type : **VN** (vehicule neuf) ou **VO** (vehicule occasion)
- VIN ou immatriculation du vehicule
- Nom et prenom du client
- Sexe du client (M/F)
- Personne morale (oui/non)
- Co-titulaire (optionnel)

### Etape 2 : Depot des documents vehicule
Le vendeur depose ses documents dans l'**espace vendeur** :

**Pour un VN (vehicule neuf) :**
| Document | Obligatoire | Info extraite |
|----------|------------|---------------|
| COC (Certificat de Conformite) | Oui | Marque, D.2 type, CNIT, VIN, energie, puissance, CO2, places, masses, classe env |
| Facture de vente | Oui | VIN, prix TTC, SIRET vendeur, date vente, couleur |

**Pour un VO (vehicule occasion) :**
| Document | Obligatoire | Info extraite |
|----------|------------|---------------|
| Carte grise (CG) | Oui | Immat, VIN, marque, D.2 type, CNIT, titulaire, adresse, toutes les cases techniques (25 champs) |
| COC (si disponible) | Recommande | Complete les infos techniques manquantes de la CG |

### Etape 3 : Suivi
Le vendeur voit dans son espace admin :
- Le diagnostic du dossier (VERT / ORANGE / ROUGE)
- Les documents manquants cote client
- Le Cerfa genere une fois le dossier complet

---

## 2. Parcours Client (Acheteur)

Le client est la personne qui achete le vehicule.

### Etape 1 : Depot des documents identite
Le client depose ses documents dans l'**espace client** :

**Personne physique :**
| Document | Obligatoire | Info extraite |
|----------|------------|---------------|
| CNI ou Passeport (recto + verso) | Oui | Nom, prenom, date naissance, lieu naissance, adresse, date expiration, n. document |
| Permis de conduire (recto + verso) | Oui | Nom, prenom, categories, date obtention |
| Justificatif de domicile | Oui | Nom, adresse, code postal, ville |
| Attestation de formation moto | Si moto 125cc/L5e | Collecte sans verification — message admin |

**Personne morale :**
| Document | Obligatoire | Info extraite |
|----------|------------|---------------|
| Kbis | Oui | SIREN, raison sociale, representant legal |
| CNI du representant legal | Oui | Identite du gerant |
| Justificatif de domicile siege | Oui | Adresse siege social |
| Permis | Non requis | — |

### Etape 2 : Fusion recto/verso
Si le client uploade le recto et le verso d'un meme document (ex: CNI recto.jpg + CNI verso.jpg), le systeme :
1. Detecte que les deux fichiers sont du meme type (CNI)
2. Fusionne le texte OCR des deux faces
3. Re-extrait les donnees du texte fusionne
4. Garde un seul document fusionne (pas de doublon)

### Etape 3 : Anti-doublon
Si le client re-uploade un document deja present :
- L'ancien est remplace par le nouveau
- Les donnees sont re-extraites
- Pas de doublon dans le dossier

---

## 3. Traitement Automatique

### 3.1 OCR (Reconnaissance de texte)
Le systeme utilise deux niveaux d'OCR :
1. **Tesseract** (gratuit, local) — traite les PDF avec texte et les scans propres
2. **Google Document AI** (payant, en fallback) — active automatiquement si Tesseract extrait moins de 50 caracteres (photos sombres, documents de mauvaise qualite)

### 3.2 Classification
Le systeme identifie automatiquement le type de document parmi 9 types :
- CNI / Passeport
- Permis de conduire
- COC (Certificat de Conformite)
- Facture
- Justificatif de domicile
- Carte grise
- Kbis
- Attestation de formation moto

### 3.3 Extraction
Pour chaque type de document, le systeme extrait les champs specifiques via des regex adaptees au format OCR :
- CNI : nom, prenom, date naissance, lieu, adresse, expiration, MRZ
- COC : 15+ champs techniques vehicule
- CG : 25 champs (toutes les cases A a Y)

### 3.4 Diagnostic
Le systeme produit un diagnostic binaire :
- **VERT** : tous les documents presents, pas d'incoherence → pret pour Cerfa
- **ORANGE** : documents presents mais avertissements → le pro decide
- **ROUGE** : document manquant ou incoherence → corrections requises

Verifications effectuees :
- VIN coherent entre tous les documents
- Nom coherent CNI ↔ domicile
- CNI non expiree
- CG barree correctement (VO)
- Kbis present si personne morale
- Permis present (sauf personne morale)

---

## 4. Generation du Cerfa

### 4.1 Processus
Quand le diagnostic est VERT ou ORANGE :
1. Le systeme construit les donnees a partir de tous les documents extraits
2. **Playwright** ouvre le formulaire officiel sur service-public.gouv.fr
3. Remplit automatiquement tous les champs (vehicule, titulaire, adresse)
4. Le site genere le Cerfa PDF officiel
5. Le systeme telecharge le PDF et le stocke dans le dossier

### 4.2 Cerfa VN (13749)
4 etapes sur le site :
1. Identification du vehicule (D.1 a V.9, couleur)
2. Certificat de vente (skip — le pro remplit a la main)
3. Demandeur / titulaire (nom, naissance, adresse, sexe/PM)
4. Telecharger le PDF

### 4.3 Cerfa VO (13750)
4 etapes sur le site :
1. Vehicule (immat, dates, marque, D.2, VIN, genre) + case Certificat cochee
2. Titulaire (personne physique/morale, nom, naissance, adresse)
3. Loueur/locataire (skip)
4. Telecharger le PDF

### 4.4 Personne morale
Si Kbis detecte :
- Case "Personne morale" cochee sur le formulaire
- SIREN + raison sociale remplis (au lieu de nom/prenom)
- Permis non exige

---

## 5. Espace Admin

Apres generation du Cerfa, l'espace admin affiche :

### 5.1 Vue dossier
- Reference du dossier
- Type (VN/VO)
- Diagnostic (VERT/ORANGE/ROUGE)
- Statut (PENDING → DIAGNOSTIC → CERFA_GENERE)

### 5.2 Documents
- **Docs vendeur** : COC, CG, facture — avec nombre de champs extraits
- **Docs client** : CNI, permis, domicile, Kbis, attestation — avec nombre de champs extraits
- Pas de doublon (fusion recto/verso, remplacement si re-upload)

### 5.3 Cerfa
- Cerfa PDF genere, telechargeable depuis l'espace admin
- Date de generation

### 5.4 Messages admin
- **VERIFICATION_MANUELLE** : si attestation de formation detectee, message pour verifier la coherence avec le permis (categorie, date obtention B, n. permis)
- Priorite HAUTE

### 5.5 Estimation taxes
- Y1 taxe regionale
- Y3 malus CO2
- Y4 taxe de gestion
- Y5 redevance acheminement
- Y6 malus au poids
- Total estime (indicatif — montant final = SIV)

---

## 6. Cas Particuliers

### 6.1 Moto avec attestation formation
Pour les motos 125cc (categorie L5e) avec permis B + formation 7h :
- Le client depose le **permis auto (B)** + l'**attestation de suivi de formation**
- Le systeme collecte les deux sans croisement automatique
- Apres generation du Cerfa, un **message admin** demande de verifier manuellement la coherence

### 6.2 Personne morale
- Detection automatique si Kbis depose
- Diagnostic ROUGE si Kbis absent pour une PM
- Permis non requis
- SIREN + raison sociale remplis sur le Cerfa

### 6.3 Co-titulaire
- Renseigne par le vendeur a la creation du dossier
- Affiche sur le Cerfa si present
- Multi-propriete cochee automatiquement

---

## 7. Stack Technique

| Composant | Technologie |
|-----------|-------------|
| Backend | Python / FastAPI |
| Frontend | React / Vite / TailwindCSS |
| OCR local | Tesseract 5.5.2 (fra) |
| OCR cloud (fallback) | Google Document AI |
| Generation Cerfa | Playwright (service-public.gouv.fr) |
| Stockage | In-memory (demo) → PostgreSQL + S3 (prod) |

---

## 8. Endpoints API

| Methode | Endpoint | Description |
|---------|----------|-------------|
| POST | /api/dossiers | Creer un dossier |
| GET | /api/dossiers | Lister les dossiers |
| GET | /api/dossiers/{id} | Detail dossier |
| POST | /api/dossiers/{id}/upload?source=vendeur | Upload doc vendeur |
| POST | /api/dossiers/{id}/upload?source=client | Upload doc client |
| POST | /api/dossiers/{id}/run-pipeline | Lancer le diagnostic |
| GET | /api/dossiers/{id}/cerfa | Generer + telecharger le Cerfa |
| GET | /api/dossiers/{id}/admin | Vue admin complete |
| GET | /api/dossiers/{id}/admin/cerfa | Telecharger le Cerfa stocke |
| DELETE | /api/dossiers/{id} | Supprimer un dossier |
