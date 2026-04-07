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

### Parametrage initial (une seule fois, a l'installation)
Lors de la premiere utilisation, le pro configure son profil. **Tous les elements sont obligatoires** — le pro ne peut pas creer de dossier tant que son profil n'est pas complet.

| Element | Utilisation |
|---------|-------------|
| **Nom du commerce** | Affiche dans le SMS recu par le client |
| **Adresse de la structure** | Affiche dans le SMS recu par le client (auto-remplie depuis le Kbis si disponible) |
| **Telephone du commerce** | Affiche dans le SMS pour que le client puisse contacter le pro |
| **Email du commerce** | Optionnel |
| **Kbis du commerce** | Identification du pro, responsabilite juridique, facturation. Le systeme extrait automatiquement SIREN, raison sociale et adresse siege. Verifie que le Kbis a moins de 3 mois (warning si perime, pas bloquant). **Ne sert PAS pour le Cerfa** (le SIREN dans le Cerfa est celui du client si PM). |
| **Photo du cachet commercial** | Appose automatiquement sur les documents (Cerfa, facture, CG, cession) |
| **Photo de la signature** | Apposee automatiquement sur les documents |
| **Assurance flotte VN** | "Votre assurance flotte couvre-t-elle les VN apres la vente ?" (oui/non) — informatif, pas de document demande |
| **Assurance flotte VO** | "Votre assurance flotte couvre-t-elle les VO apres la vente ?" (oui/non) — informatif, pas de document demande |

Les infos du commerce (nom, adresse, telephone) sont integrees dans le SMS envoye au client pour qu'il sache **qui lui ecrit et pourquoi**. Le cachet et la signature sont reutilises automatiquement sur tous les dossiers. Le Kbis permet d'identifier formellement la structure du pro pour notre gestion interne (facturation, responsabilite, anti-fraude).

**Assurance vehicule — gestion par le pro (pour chaque dossier) :**

L'assurance flotte du pro n'est pas un document demande dans l'espace depot vendeur. Pour chaque dossier, le systeme pose deux questions au pro :

```
Question 1 : "Avez-vous une assurance flotte qui couvre le vehicule
              vendu au client en attendant la validation au SIV ?"
│
├─ OUI → pas d'attestation assurance dans la checklist client. Termine.
│
└─ NON → Question 2 :
    "Souhaitez-vous que l'on demande a votre client
     son attestation d'assurance ?"
    │
    ├─ OUI → attestation assurance ajoutee comme OBLIGATOIRE
    │         dans la checklist client
    │
    └─ NON → pas d'attestation dans la checklist client. Termine.
             Le pro gere directement avec son client.
```

Le pro **decide et valide** — rien n'est automatique.

**Verifications sur l'attestation d'assurance (si deposee, VN et VO) :**

| Verification | Resultat si probleme |
|---|---|
| **C'est bien une assurance auto** (mots-cles : auto, vehicule, carte verte, RC) | ⛔ BLOCAGE : "Document non reconnu comme assurance automobile" |
| **Nom assure = nom CNI client** | Fichier → ⛔ BLOCAGE + demande photo / Photo → ⚠ Warning |
| **Assurance non expiree** | ⛔ BLOCAGE : "Assurance expiree — fournir une attestation valide" |

Ces verifications s'appliquent uniquement quand le pro a demande l'attestation au client et que le client l'a deposee. Pas de croisement sur l'immatriculation ou le VIN (pas toujours present sur l'attestation, et inexistant en VN).

**Avertissement au pro :** quand le pro valide la demande de collecte d'attestation aupres de son client, le systeme l'informe clairement :

> "C'est note ! L'attestation sera demandee a votre client. De notre cote, on verifiera que c'est bien une assurance auto et que le nom correspond au dossier. Pensez a verifier vous-meme que l'assurance couvre bien le vehicule avant de soumettre au SIV — c'est un point que vous maitrisez mieux que nous !"

Le ton est bienveillant mais le message est clair : Imatra fait les verifications de base (type de doc + nom), le pro garde la main sur la verification de couverture.

### Etape 1 : Creation du dossier (saisie ultra-minimale)
Le vendeur cree un nouveau dossier dans son espace admin. Il ne saisit que **le numero de portable du client** — tout le reste est deduit automatiquement.

**Champs saisis par le pro :**

| Champ | Obligatoire | Note |
|-------|------------|------|
| Portable du client | Oui | Indispensable pour l'envoi du lien SMS |
| Email du client | Optionnel | Lien envoye aussi par email si renseigne |

**Tout le reste est deduit automatiquement :**

| Info | Source | Comment |
|------|--------|---------|
| Type VN ou VO | Documents pro | CG barree detectee → VO. COC + Facture → VN |
| VIN | Documents pro | Extrait du COC (VN) ou CG barree (VO) |
| Immatriculation | Documents pro | Extraite de la CG barree (VO) |
| Nom et prenom client | Documents pro | Extraits de la facture (VN) ou CG barree (VO) |
| Sexe du client | Prenom (CNI) | Deduit automatiquement du prenom extrait de la CNI |
| Personne morale | Documents client | Le client indique s'il est PM dans sa page d'upload. Detecte auto si Kbis uploade. |
| Co-titulaire | Page client | Le client renseigne le co-titulaire dans sa page d'upload |

### Etape 2 : Depot des documents vehicule (avec checklist interactive)
Le vendeur depose ses documents dans l'**espace vendeur**. L'espace presente la liste des documents attendus pour les deux cas (VN et VO). Chaque document est analyse **immediatement** a la depose.

**Liste des documents presentee au pro :**

| Pour un VN (vehicule neuf) | | Pour un VO (vehicule occasion) |
|---|---|---|
| COC (obligatoire) | | Carte grise barree (obligatoire) |
| Facture de vente (obligatoire) | | COC (recommande) |

Le pro n'a pas besoin de preciser VN ou VO — il depose ses documents et le systeme detecte automatiquement le type de dossier.

**Flux de validation en temps reel :**
1. Le pro depose un fichier (drag & drop ou selection)
2. **Tesseract OCR** (local, gratuit) analyse le document
3. Si Tesseract echoue (confidence < 40% ou < 50 caracteres) → **Google Document AI** prend le relais automatiquement
4. Le resultat s'affiche immediatement dans l'espace de depot :
   - **OK** (vert) : document lisible, type detecte, donnees extraites affichees
   - **Avertissement** (orange) : donnees extraites mais qualite moyenne, re-depot recommande
   - **Illisible** (rouge) : les deux OCR ont echoue, message d'erreur + conseil pour re-deposer

### Checklist interactive (visible en permanence)
L'espace de depot affiche en permanence une **checklist interactive** qui montre au pro exactement ou il en est. Chaque element a un statut clair et une action a effectuer si necessaire.

**La checklist couvre 3 blocs :**

**1. Profil du commerce (toujours vert — renseigne au parametrage initial) :**
Ces infos sont sauvegardees lors de l'installation et ne peuvent pas etre manquantes dans l'espace de depot (le pro ne peut pas acceder a la page d'upload sans avoir complete son profil). Elles sont affichees en vert pour confirmer visuellement que tout est pris en compte.
| Element | Statut |
|---------|--------|
| Nom du commerce | ✅ toujours ok |
| Adresse de la structure | ✅ toujours ok |
| Telephone du commerce | ✅ toujours ok |
| Cachet commercial | ✅ toujours ok |
| Signature | ✅ toujours ok |
| Kbis du commerce | ✅ toujours ok (+ SIREN et raison sociale extraits) |

**2. Information client :**
| Element | Statut | Action si manquant |
|---------|--------|-------------------|
| Portable du client | ok / manquant | Renseignez le numero |

**3. Documents vehicule :**
| Element | Statut | Action si probleme |
|---------|--------|-------------------|
| COC / CG barree / Facture | ok / illisible / manquant | Re-deposez un scan plus net / Deposez le document |
| Type de dossier (VN/VO) | detecte / en attente | Deposez un document pour que le type soit detecte |

**Regle de blocage :**
- **Tant qu'un seul element est manquant ou illisible (info client ou documents) → pas de bouton de validation cliquable, pas de recapitulatif, pas d'envoi de lien**
- Le bouton "Valider et envoyer le lien au client" n'apparait (ou ne devient cliquable) que lorsque la checklist est **100% verte**
- La checklist est consultable a tout moment via l'endpoint `GET /api/dossiers/{id}/checklist`

**Documents et infos extraites :**

**VN (vehicule neuf) :**
| Document | Obligatoire | Info extraite |
|----------|------------|---------------|
| COC (Certificat de Conformite) | Oui | Marque, D.2 type, CNIT, VIN, energie, puissance, CO2, places, masses, classe env |
| Facture de vente | Oui | VIN, prix TTC, SIRET vendeur, date vente, couleur, nom client |

**VO (vehicule occasion) :**
| Document | Obligatoire | Info extraite |
|----------|------------|---------------|
| Carte grise barree | Oui | Immatriculation, VIN, marque, titulaire, nom acheteur (barre), date vente (barre), 25 champs techniques |
| Certificat de cession (Cerfa 15776) signe | Oui (par defaut) | Nom vendeur, nom acquereur, date cession, VIN, immatriculation, signatures |
| COC (si disponible) | Recommande | Complete les infos techniques pour le Cerfa |

**Option "Pas de certificat de cession" :**
Si le pro coche cette option, le certificat de cession n'est plus requis dans son espace de depot. A la place :
- Le systeme **genere** le certificat de cession pre-rempli
- Le vendeur le signe automatiquement (cachet + signature)
- Le client le signe numeriquement via le lien SMS (doigt + OTP)
- La signature client n'est requise qu'en VO et **uniquement si le certificat de cession n'a pas ete depose**

**Apres signature de la cession par le client — telechargement obligatoire :**

```
Client signe la cession (doigt + OTP)
    │
    ├─ PDF final genere (signatures vendeur + client)
    │
    ├─ Message : "Telechargez votre certificat de cession signe.
    │             Ce document est obligatoire, conservez-le precieusement."
    │
    ├─ [Telecharger mon certificat de cession] ← bouton
    │
    └─ Tant que PAS telecharge → les uploads suivants sont BLOQUES
       Le client ne peut pas continuer sans avoir telecharge son exemplaire.
```

Ce mecanisme garantit que le client repart avec son exemplaire du certificat de cession signe.

**Croisements sur le certificat de cession depose :**

| Verification | Documents croises | Resultat si incoherence |
|---|---|---|
| **Date de vente CG barree = date cession 15776** | CG barree ↔ Certificat cession | Fichier → ⛔ BLOCAGE / Photo → ⚠ Warning |
| **Nom acquereur 15776 = nom CNI client** | Certificat cession ↔ CNI | Fichier → ⛔ BLOCAGE / Photo → ⚠ Warning |
| **Nom acheteur barre CG = nom CNI client** | CG barree ↔ CNI | Fichier → ⛔ BLOCAGE / Photo → ⚠ Warning |

### Etape 3 : Recapitulatif et validation par le pro
Une fois tous les docs pro lisibles et valides, un **recapitulatif** s'affiche dans l'espace de depot. Le pro doit le verifier et **cocher une case pour confirmer** l'envoi du lien au client. Le lien ne part **jamais automatiquement**.

**Contenu du recapitulatif :**

| Bloc | Informations affichees |
|------|----------------------|
| **Type de dossier** | VN ou VO (detecte automatiquement) |
| **Vehicule** | VIN, immatriculation (VO), marque, modele, CNIT, energie, puissance, CO2 |
| **Vente** | Prix TTC, date vente, SIRET vendeur (VN) |
| **Client** | Nom, prenom (extraits des docs), telephone, email |
| **Documents deposes** | Liste avec statut de chaque doc (ok / avertissement) |

> **Message :** "Dossier [VN/VO] detecte. Verifiez les informations ci-dessous puis validez pour envoyer le lien securise au [06XXXXXXXX]. Votre client pourra y deposer ses documents d'identite pour completer la demarche de generation du Cerfa."

**Action requise :** le pro coche la case "Je confirme les informations et j'autorise l'envoi du lien au client".

### Etape 4 : Envoi du lien client (SMS personnalise)
Une fois que le pro a valide le recapitulatif, le systeme envoie un **SMS personnalise** au client :

> Bonjour Jean, **Moto Center Paris** a choisi **Imatra** pour votre carte grise. Deposez **gratuitement** vos documents ici : https://... Infos & confidentialite : cartegrisepro.fr/confidentialite — Contact : Moto Center Paris au 01 23 45 67 89

**~250 caracteres** (2 SMS max). Contient l'essentiel :
- **Qui** : le commerce (Moto Center Paris)
- **Via quoi** : notre service (Imatra)
- **Pourquoi** : carte grise
- **Gratuit** : "deposez gratuitement"
- **Lien securise** vers la page de depot
- **Lien RGPD** : politique de confidentialite (conformite article 13 RGPD — information en deux niveaux, recommandation CNIL pour supports a espace limite)
- **Contact** : telephone du commerce

**Conformite RGPD — approche en deux niveaux :**

**Niveau 1 — le SMS (information minimale) :**
- Identite du responsable de traitement (Imatra)
- Finalite implicite (carte grise)
- Lien vers la politique de confidentialite complete

**Niveau 2 — la page d'upload (information complete) :**
Quand le client ouvre le lien, la page doit afficher avant le premier upload :
- Identite et coordonnees du responsable de traitement (Imatra)
- Finalite du traitement : demande d'immatriculation vehicule
- Base legale : consentement (article 6.1.a RGPD)
- Destinataires : le vendeur pro, le systeme Imatra
- Duree de conservation : documents supprimes apres finalisation de la demarche
- Droits du client : acces, rectification, suppression, portabilite, opposition
- Contact DPO : adresse email dediee
- **Case de consentement obligatoire** a cocher avant le premier depot de document

Le client doit **consentir explicitement** avant de deposer son premier document.

Le pro est notifie dans son espace que le lien a ete envoye. Il n'a rien a faire — il attend que le client uploade ses documents.

### Etape 5 : Suivi
Le vendeur voit dans son espace admin :
- Le statut du dossier (VERT = pret / ROUGE = blocage)
- Les documents manquants cote client
- Le Cerfa genere une fois le dossier complet

### Etape 4 : Suivi
Le vendeur voit dans son espace admin :
- Le statut du dossier (VERT = pret / ROUGE = blocage)
- Les documents manquants cote client
- Le Cerfa genere une fois le dossier complet

---

## 2. Documents Client (Acheteur)

Le client est la personne qui achete le vehicule.

**Pas d'espace client sur le site du commercant.** Une fois que le pro a valide le recapitulatif et confirme l'envoi, le client recoit un **lien securise par SMS**. Il ouvre une page d'upload simple. Pas de compte a creer, pas de login. En VO, le meme lien permet aussi de signer la cession numeriquement (voir section 4.6).

### Ce que le client voit quand il ouvre le lien

**1. En-tete de confiance :**
La page affiche immediatement les infos du commerce pour que le client sache d'ou ca vient :
- Nom du commerce (ex: "Moto Center Paris")
- Adresse du commerce
- Telephone du commerce
- Mention "a choisi Imatra pour votre demarche de carte grise"

**2. Mentions RGPD (affichees avant toute action) :**
Conformement a l'article 13 du RGPD, la page affiche :
- **Responsable de traitement** : Imatra
- **Finalite** : traitement de la demande d'immatriculation vehicule (carte grise) initiee par le vendeur
- **Base legale** : consentement (article 6.1.a RGPD)
- **Destinataires** : le vendeur pro et Imatra
- **Conservation** : documents supprimes automatiquement une fois le dossier finalise
- **Droits** : acces, rectification, suppression, portabilite, opposition — contact : rgpd@cartegrisepro.fr
- **Lien** vers la politique de confidentialite complete (cartegrisepro.fr/confidentialite)

**3. Consentement obligatoire (case a cocher) :**
Le client doit cocher avant de pouvoir deposer son premier document :

> ☐ J'accepte que mes documents d'identite soient traites par Imatra et transmis a [Moto Center Paris] dans le seul but de realiser ma demande de carte grise. J'ai pris connaissance de la politique de confidentialite.

**Tant que le consentement n'est pas coche, l'upload est bloque** (le bouton de depot reste grise).

**4. Choix du mode de reception du CPI (obligatoire avant upload) :**
Le client choisit comment il souhaite recevoir son Certificat d'Immatriculation Provisoire :

> ○ **En main propre** — Je recupererai mon CPI aupres de [Moto Center Paris]
> ○ **Par email** — Je souhaite recevoir mon CPI par email : [________@____.__]

Si le client choisit "par email", il doit saisir son adresse email. Ce choix est transmis au vendeur pour qu'il sache comment remettre le CPI.

**Tant que le choix CPI n'est pas fait, l'upload est bloque.**

### Questions posees au client (apres consentement et choix CPI)
Le client repond a deux questions simples :

### Depot des documents (photo ou fichier)
Pour chaque document de la checklist, le client a **deux options** :

| Option | Bouton | Comportement |
|--------|--------|-------------|
| **Prendre en photo** | Icone appareil photo | Ouvre l'appareil photo. Pour les documents recto/verso (CNI, permis), le systeme guide le client : d'abord le recto, puis le verso. Les deux photos sont fusionnees automatiquement en un seul document. |
| **Choisir un fichier** | Icone dossier | Selectionner un scan/photo existant (PDF, JPEG, PNG). Si le fichier contient deja recto+verso (PDF 2 pages ou scan double), le systeme le detecte. |

**Flux photo pour les documents recto/verso (CNI, permis) :**

```
[📷 Photographier ma CNI]
     │
     ├─ Etape 1 : "Photographiez le RECTO de votre CNI"
     │             → le client prend la photo
     │             → apercu affiche : "Recto capture ✓"
     │
     ├─ Etape 2 : "Retournez le document et photographiez le VERSO"
     │             → le client prend la photo
     │             → apercu affiche : "Verso capture ✓"
     │
     └─ Fusion automatique recto + verso
        → OCR sur les deux faces
        → extraction des donnees combinees
        → resultat affiche dans la checklist : "CNI ✅"
```

**Flux photo pour les documents simple face (domicile, attestation, assurance) :**

```
[📷 Photographier mon justificatif]
     │
     └─ Une seule photo → OCR → resultat affiche
```

**La checklist reste simple — un seul element par document :**

```
☐ CNI ou Passeport       [📷 Photo]  [📁 Fichier]
☐ Permis de conduire     [📷 Photo]  [📁 Fichier]
☐ Justificatif domicile  [📷 Photo]  [📁 Fichier]
```

Le recto/verso est gere a l'interieur du flux photo, pas comme deux lignes separees. Le client ne voit qu'un seul element par document dans sa checklist.

Dans les deux cas (photo ou fichier), le document est envoye au backend et traite par le meme pipeline OCR.

### Feedback temps reel (meme approche que cote pro)
Chaque document depose (photo ou fichier) est analyse **immediatement** :
1. Le client prend une photo ou selectionne un fichier
2. Le document est envoye au backend
3. **Tesseract OCR** analyse le document
4. Si Tesseract echoue (confidence < 40%) → **Google Document AI** prend le relais
5. Le resultat s'affiche immediatement dans la checklist :
   - **OK** (vert) : document lisible, type detecte, donnees extraites
   - **Avertissement** (orange) : qualite moyenne, re-depot recommande
   - **Illisible** (rouge) : message d'erreur + conseil (meilleur eclairage, eviter reflets, poser le document bien a plat)

### Checklist dynamique (se met a jour apres chaque depot)
La page d'upload affiche une **checklist qui s'adapte en temps reel** selon ce que le client a deja depose et les infos du vehicule :

**Reglementation permis integree — le systeme croise automatiquement les donnees du COC (categorie, puissance, debridabilite) avec les categories du permis depose par le client :**

**Tableau reglementaire :**

| Categorie vehicule | Puissance | Permis requis | Alternative permis B |
|--------------------|-----------|---------------|----------------------|
| L1e (cyclomoteur) | ≤ 4 kW | AM | B suffit (AM inclus) |
| L3e 125cc | ≤ 11 kW | A1 | B + formation 7h (B ≥ 2 ans) |
| L3e intermediaire | ≤ 35 kW | A2 | Non — B insuffisant |
| L3e puissant | > 35 kW | A | Non — 2 ans de A2 + formation |
| L5e (tricycle) | ≤ 15 kW | A1 (min 16 ans) | B + formation 7h (B ≥ 2 ans) |
| L5e puissant (tricycle) | > 15 kW | A (min 21 ans) | B + formation 7h (B ≥ 2 ans **ET age ≥ 21 ans**) |
| Moto electrique | Memes seuils kW | Idem | Pas de cylindree, seule la puissance compte |

**Verification d'age automatique :**
Le systeme extrait la date de naissance de la CNI et verifie l'age minimum selon le vehicule :

| Permis | Age minimum | Condition |
|--------|-------------|-----------|
| AM | 14 ans | — |
| A1 | 16 ans | — |
| A2 | 18 ans | — |
| A | 20 ans | Via 2 ans de A2 + formation complementaire |
| A (acces direct) | 24 ans | Sans passer par A2 |
| B + formation 7h (tricycle > 15 kW) | 21 ans | Specifique aux tricycles L5e puissants |

Si l'age du client est insuffisant → ⛔ BLOCAGE avec message explicatif.

**Note :** Le controle technique (CT) n'est pas gere par le systeme. Le CT est de la responsabilite du vendeur professionnel avant la vente et ne fait pas partie du perimetre de la demande de carte grise.

**Verification anciennete permis B pour formation 7h (art. R221-1) :**
Si le vehicule accepte B + formation 7h (≤ 11 kW), le systeme verifie automatiquement la date d'obtention du permis B :

| Anciennete permis B | Resultat |
|---------------------|----------|
| **Avant le 1er mars 1980** | EXEMPT de formation — aucune attestation requise |
| **≥ 2 ans** | Eligible — attestation de formation 7h demandee dans la checklist |
| **< 2 ans** | ⛔ BLOCAGE — "Permis B trop recent. Eligible a partir du JJ/MM/AAAA. Permis A1 requis." |
| **Date non extractible** | ⛔ BLOCAGE par securite — impossible de verifier l'anciennete |

**Verification en deux temps (calcul en annees civiles, pas en jours) :**
1. **Si attestation de formation deja deposee** → le systeme verifie que la date du permis B + 2 ans ≤ date de l'attestation. Si la formation a eu lieu avant les 2 ans du permis B → attestation invalide, blocage.
2. **Si attestation pas encore deposee** → le systeme verifie que la date du permis B + 2 ans ≤ aujourd'hui. Sinon la formation n'a pas pu etre faite, blocage.

Le calcul utilise des annees civiles (`date_B.annee + 2`) et non un nombre de jours fixe, pour rester correct dans le temps.

**Cas particuliers detectes automatiquement :**

| Cas | Detection | Consequence |
|-----|-----------|-------------|
| **Vehicule debridable** | Le COC mentionne "converting between subcategories A2/A3" | La categorie affichee (ex: L3e-A1E) ne reflete pas la puissance reelle. Le systeme exige le permis correspondant a la categorie la plus haute mentionnee (A2 ou A). **Le permis B + formation 7h ne suffit pas.** |
| **Puissance non extractible** | L'OCR n'a pas pu lire la puissance du COC | Le systeme ne conclut PAS que B + formation suffit. Il exige un permis moto (A2 minimum) par securite et demande une verification manuelle du COC. |
| **Moto electrique bridee** (ex: Stark VARG L3e-A1E) | Categorie A1E mais COC mentionne conversion A2/A3 | Permis A requis — la puissance crete depasse largement le seuil A1. Le bridage a 11 kW en continu ne change pas l'exigence de permis pour la version debridable. |

**Exemples d'adaptation dynamique de la checklist :**

| Evenement | Effet sur la checklist |
|-----------|----------------------|
| Client uploade un **Kbis** | → PM detectee → **permis retire**, **Kbis** et **CNI representant legal** ajoutes |
| Vehicule = **scooter electrique 8 kW (L3e-A1E, non debridable)** + **permis B** | → Attestation formation 7h ajoutee (B + formation suffit) |
| Vehicule = **moto electrique L3e-A1E debridable A2/A3** (ex: Stark VARG) + **permis B** | → ⛔ **BLOCAGE** : "Vehicule debridable — permis A requis. Le permis B + formation ne suffit pas." |
| Vehicule = **moto 25 kW** + **permis B** | → ⛔ **BLOCAGE** : "Permis A2 requis — le permis B ne suffit pas" |
| Vehicule = **moto 50 kW** + **permis A2** | → ⛔ **BLOCAGE** : "Permis A requis (2 ans de A2 + formation)" |
| Vehicule = **moto 25 kW** + **permis A2** | → ✅ OK |
| Vehicule = **cyclomoteur 3 kW** + **permis B** | → ✅ OK (B inclut AM) |
| **Puissance non lisible dans le COC** + **permis B** | → ⛔ **BLOCAGE** : "Puissance non verifiable — permis moto requis par securite" |
| Client repond **"co-titulaire oui"** | → Le co-titulaire recevra son propre lien SMS |

**Principe de securite : en cas de doute, le systeme ne conclut JAMAIS que le permis B suffit.** Il exige le permis moto et demande une verification.

Le message reglementaire est affiche au client des que le vehicule est un deux-roues motorise, **meme avant le depot du permis**, pour qu'il sache quel permis est attendu.

La checklist affiche a tout moment :
- Documents deposes et leur statut (ok / avertissement / illisible)
- Documents encore manquants (avec la raison et le message reglementaire)
- **Blocages reglementaires** si le permis est insuffisant pour le vehicule
- **Alertes debridabilite** si le COC mentionne une conversion possible
- Le client sait exactement ou il en est a chaque instant

**Verrou : le diagnostic et la generation du Cerfa sont bloques tant que les documents client sont incomplets, illisibles, ou qu'un blocage reglementaire est detecte.**

### Recapitulatif et confirmation d'envoi (quand tous les docs sont deposes)
Une fois que tous les documents requis sont deposes et valides, le client voit un **recapitulatif** de tout ce qu'il a depose. Il doit **confirmer explicitement** l'envoi au vendeur — les documents ne sont pas transmis automatiquement.

**Etape 1 — Recapitulatif :**
> Tous vos documents sont deposes et valides.
> Verifiez la liste ci-dessous puis confirmez l'envoi a [Nom commerce].
>
> Documents deposes :
> ✅ CNI — carian_cni.jpg
> ✅ Permis de conduire — permis_recto_verso.jpg
> ✅ Justificatif de domicile — edf_mars2026.pdf
>
> ⚠ **Adresse d'envoi de votre carte grise :**
> Votre carte grise definitive sera envoyee par courrier securise a l'adresse
> figurant sur votre justificatif de domicile :
> **8 Place de la Tourbie, 29000 Quimper**
> C'est cette adresse qui sera inscrite sur votre certificat d'immatriculation.
> *Si cette adresse n'est pas correcte, remplacez votre justificatif de domicile avant de confirmer.*
>
> ☐ Je confirme l'envoi de mes documents a [Nom commerce]
>   pour le traitement de ma demande de carte grise.
>
> [Envoyer mes documents] ← bouton cliquable seulement si coche

**Etape 2 — Message de remerciement (apres confirmation) :**
> **Merci ! Vos documents ont bien ete transmis a [Nom commerce].**
> Votre dossier de carte grise va etre finalise.
>
> **Prochaines etapes :**
> 1. [Nom commerce] va verifier votre dossier et soumettre la demande aupres du SIV.
> 2. **Si email :** [Nom commerce] vous enverra votre CPI par email a xxx@xxx une fois qu'il aura finalise le dossier aupres du SIV. / **Si main propre :** [Nom commerce] vous contactera directement une fois qu'il aura finalise le dossier aupres du SIV pour que vous puissiez recuperer votre CPI. Ce document vous permettra de circuler pendant 1 mois.
> 3. Votre carte grise definitive vous sera envoyee par courrier securise (Imprimerie Nationale) a l'adresse figurant sur le justificatif de domicile que vous avez depose — c'est cette adresse qui sera inscrite sur votre certificat d'immatriculation. Delai : 3 a 7 jours ouvrables.
>
> Pour toute question, contactez [Nom commerce] au [telephone].

Le message adapte l'etape 2 en fonction du choix du client (email ou main propre).

### Reprise de session
Le client peut **fermer la page a tout moment** sans perdre ses documents. Quand il reouvre le lien recu par SMS :
- Ses documents deja deposes sont sauvegardes
- La checklist est mise a jour avec l'etat actuel
- Le consentement RGPD reste valide (pas besoin de re-cocher)
- Il reprend exactement la ou il en etait

Un message est affiche en permanence : *"Vous pouvez fermer cette page a tout moment. Vos documents sont sauvegardes. Reouvrez le lien pour reprendre."*

### Suppression et remplacement de documents
A tout moment (tant que l'envoi n'a pas ete confirme), le client peut **supprimer** n'importe quel document depose et en deposer un nouveau a la place. Cela concerne tous les types de documents :

- CNI / Passeport
- Permis de conduire
- Justificatif de domicile
- Kbis (personne morale)
- Attestation de formation 7h
- Attestation d'assurance

**Fonctionnement :**
- Chaque document dans la checklist a un bouton **Supprimer** (icone corbeille)
- Le document est retire de la liste
- La checklist et les documents attendus se **recalculent dynamiquement** :
  - Suppression du Kbis → le Kbis est re-demande (personne morale reste coche). Si le client decoche "personne morale" → permis redevient obligatoire
  - Suppression du permis → les verifications categorie/age/anciennete sont reinitialisees
  - Suppression de la CNI → sexe deduit et verifications de coherence reinitialises
- Le client peut re-deposer un nouveau document (photo ou fichier)
- **Bloque apres confirmation d'envoi** — une fois les documents envoyes, toute modification doit passer par le vendeur

### Desactivation du lien
Une fois le dossier finalise (Cerfa genere), le lien SMS est **desactive**. Si le client reouvre le lien apres finalisation, il voit :

> **Merci, vos documents ont bien ete transmis.**
> Votre dossier de carte grise est en cours de finalisation par [Nom commerce].
>
> **Prochaines etapes :**
> 1. [Nom commerce] va soumettre votre dossier aupres de l'administration (SIV).
> 2. [Nom commerce] vous remettra votre Certificat d'Immatriculation Provisoire (CPI) en main propre ou par email. Ce document vous permet de circuler pendant 1 mois.
> 3. Vous recevrez votre carte grise definitive par courrier securise (lettre suivie de l'Imprimerie Nationale) a l'adresse indiquee sur votre justificatif de domicile, sous 3 a 7 jours ouvrables.
>
> Pour toute question, contactez [Nom commerce] au [telephone].

**Le client ne recoit PAS le Cerfa** — c'est un document administratif que le pro soumet au SIV. Le client recoit uniquement :
- Son **exemplaire du certificat de cession** (VO, si genere par le systeme — telechargement obligatoire)
- La **nouvelle carte grise** une fois emise par le SIV (remise par le pro, hors perimetre du systeme)

### Questions posees au client (dans la page d'upload)
Avant de deposer ses documents, le client repond a deux questions simples :

1. **"Vous achetez en tant que societe (personne morale) ?"**
   - Si oui → un Kbis sera demande, le permis ne sera plus requis
   - Si un Kbis est uploade, la personne morale est detectee automatiquement
2. **"Y a-t-il un co-titulaire pour ce vehicule ?"**
   - Si oui → le co-titulaire recoit son propre lien SMS pour deposer ses documents et signer (VO)

Ces informations ne sont **pas demandees au pro** — c'est le client qui les renseigne.

### Infos deduites automatiquement cote client
- **Sexe** : deduit du prenom extrait de la CNI (heuristique sur les terminaisons des prenoms francais)
- **Personne morale** : detectee automatiquement si le client uploade un Kbis (SIREN + raison sociale extraits)
- **Vehicule moto** : detecte depuis la categorie J du COC (L1e a L7e) ou le genre national (MTL, MTT1, etc.)

### Verification de la piece d'identite (CNI ou passeport)
Quand le client depose sa CNI ou son passeport, le systeme verifie automatiquement :

| Verification | CNI | Passeport | Resultat si probleme |
|---|---|---|---|
| **Date d'expiration** | Oui | Oui | ⛔ BLOCAGE : "Document expire — renouvelez ou fournissez un autre document" |
| **Regle 2004-2013** | Oui (si delivree entre 2004 et 2013 a un majeur → +5 ans) | Non applicable | ℹ INFO : "Validite etendue jusqu'au JJ/MM/AAAA" |
| **Date non lisible** | ⚠ Warning | ⚠ Warning | "Verifiez que le document est en cours de validite" |
| **Numero de document** | Extrait (12 chiffres) | Extrait (format XX AA XXXXX) | — |
| **MRZ** | 1 ligne (IDFRA...) | 2 lignes (P<FRA...) — nom, prenom, numero extraits | — |
| **Pays emetteur** | — | Extrait (doit etre FRA ou UE) | — |

**Reconnaissance automatique CNI vs Passeport :**
Le systeme distingue les deux documents par les mots-cles et la MRZ :
- MRZ commencant par `P<FRA` → passeport
- Mots-cles "carte nationale d'identite" → CNI
- Mots-cles "passeport" / "passport" → passeport

Les deux sont acceptes comme piece d'identite valide. Le client peut deposer l'un ou l'autre.

### Verification du permis de conduire
Quand le client depose son permis, le systeme verifie automatiquement :

| Verification | Ce qui est verifie | Resultat si probleme |
|---|---|---|
| **Validite** | Date d'expiration (champ 4b) vs date du jour | ⛔ BLOCAGE : "Permis expire le JJ/MM/AAAA — renouvelez votre permis" |
| **Categories vs vehicule** | Permis B present pour voiture, A/A1/A2 pour moto | ⛔ BLOCAGE : "Categorie B absente du permis" |
| **Coherence nom** | Nom sur le permis vs nom sur la CNI | Depend du mode de depot (voir ci-dessous) |
| **Ancien format (rose)** | Pas de date d'expiration | ✅ Considere valide (les droits de conduire restent valables) |

**Regle universelle pour TOUTE incoherence entre documents :**

| Mode de depot | Resultat |
|---|---|
| **Fichier** (scan, galerie) | ⛔ BLOCAGE : "Incoherence detectee — reprenez les documents en photo directement". La qualite du scan peut expliquer l'erreur OCR. |
| **Photo directe** (appareil photo) | ⚠ AVERTISSEMENT : "Incoherence detectee — verifiez". Pas bloquant car la photo est plus fiable. |

Cette regle s'applique a TOUTES les incoherences : nom, date de naissance, lieu de naissance, entre tout couple de documents (CNI↔permis, CNI↔domicile, etc.).

Ce mecanisme sert aussi de premier niveau anti-fraude : il est plus difficile de deposer un document falsifie via photo directe que via fichier.

### Croisements inter-documents
Quand plusieurs documents sont deposes, le systeme croise automatiquement les informations :

**CNI/Passeport ↔ Permis :**

| Verification | Resultat si incoherence |
|---|---|
| **Date de naissance** | Fichier → ⛔ BLOCAGE + demande photo / Photo → ⚠ Warning |
| **Commune de naissance** | Fichier → ⛔ BLOCAGE + demande photo / Photo → ⚠ Warning |
| **Nom** | Fichier → ⛔ BLOCAGE + demande photo / Photo → ⚠ Warning |

**CG barree ↔ CNI/Passeport client :**

| Verification | Resultat si incoherence |
|---|---|
| **Nom acheteur inscrit sur la barre** ↔ **Nom CNI client** | Fichier → ⛔ BLOCAGE + demande photo / Photo → ⚠ Warning |

Le nom de l'acheteur est inscrit par le vendeur sur la barre horizontale qui traverse la CG (obligation legale). Le systeme extrait ce nom et le croise avec la CNI du client pour verifier que la CG barree est bien au nom du bon acheteur.

Ces verifications garantissent que tous les documents sont coherents et appartiennent bien a la meme personne.

### Departement de naissance (pour le Cerfa)
Le Cerfa demande la commune ET le departement de naissance. Le systeme :
- Extrait la **commune de naissance** depuis la CNI/passeport
- **Deduit automatiquement le departement** a partir de la commune (table des villes/prefectures françaises)
- Si la commune n'est pas reconnue → le champ reste vide, le pro devra le verifier

**Important** : l'adresse de domicile pour le Cerfa vient UNIQUEMENT du **justificatif de domicile**, jamais de la CNI/passeport (l'adresse sur la piece d'identite peut etre obsolete).

Ces verifications s'ajoutent aux controles specifiques moto (categories, formation 7h, age, anciennete B) detailles ci-dessus.

### Documents identite requis
Le client uploade les documents suivants via le lien recu :

**Personne physique :**
| Document | Obligatoire | Info extraite |
|----------|------------|---------------|
| CNI ou Passeport (recto + verso) | Oui | Nom, prenom, date naissance, lieu naissance, adresse, date expiration, n. document |
| Permis de conduire (recto + verso) | Oui | Nom, prenom, categories, date obtention |
| Justificatif de domicile | Oui | Nom, adresse, code postal, ville |
| Attestation de formation moto | Si moto 125cc/L5e | Collecte sans verification — message admin |
| Attestation d'assurance | Optionnel | Collecte sans verification — message admin pour verification |

**Note :** si l'attestation d'assurance n'est pas fournie par le client, un message est envoye a l'admin sur son espace pour suivi.

**Signature client :**
- **VN** : aucune signature client requise. Le pro soumet comme professionnel vendeur.
- **VO** : le client signe uniquement la **cession 15776** (en tant qu'acquereur) via signature numerique (doigt + OTP SMS). Voir section 4.6.

Le cachet/signature du pro est appose automatiquement sur tous les autres documents. Voir section 4.7.

**Personne morale :**
| Document | Obligatoire | Info extraite |
|----------|------------|---------------|
| Kbis | Oui | SIREN, raison sociale, representant legal |
| CNI du representant legal | Oui | Identite du gerant |
| Justificatif de domicile siege | Oui | Adresse siege social |
| Carte grise barree (VO uniquement) | Oui (VO) | Immat, VIN, marque, titulaire, cases techniques |
| Attestation d'assurance | Optionnel | Collecte sans verification — message admin |
| Permis | Non requis | — |

### Fusion recto/verso
Si le client uploade le recto et le verso d'un meme document (ex: CNI recto.jpg + CNI verso.jpg), le systeme :
1. Detecte que les deux fichiers sont du meme type (CNI)
2. Fusionne le texte OCR des deux faces
3. Re-extrait les donnees du texte fusionne
4. Garde un seul document fusionne (pas de doublon)

### Anti-doublon
Si le client re-uploade un document deja present :
- L'ancien est remplace par le nouveau
- Les donnees sont re-extraites
- Pas de doublon dans le dossier

---

## 3. Traitement Automatique

### 3.1 OCR (Reconnaissance de texte)
Le systeme utilise deux niveaux d'OCR avec fallback automatique :
1. **Tesseract** (gratuit, local) — traite les PDF avec texte et les scans propres
2. **Google Document AI** (payant, en fallback) — active automatiquement si Tesseract a une confidence < 40% ou extrait moins de 50 caracteres

**Seuils de qualite :**
- **< 40% confidence** → document illisible (BLOQUANT — les deux OCR ont echoue)
- **40-70% confidence** → avertissement, donnees extraites mais erreurs possibles
- **>= 70% confidence** → OK

L'OCR est execute **immediatement** a la depose de chaque document (cote pro ET cote client), avec feedback temps reel dans l'interface.

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

### 3.4 Regle de blocage
**Le diagnostic et la generation du Cerfa sont bloques tant que :**
- Un document obligatoire est manquant (cote pro OU cote client)
- Un document est illisible (cote pro OU cote client)

Ce verrou s'applique a toute la chaine : envoi lien client (si docs pro incomplets/illisibles) → diagnostic (si docs client incomplets/illisibles) → generation Cerfa (si n'importe quel element bloquant). Le systeme retourne les blocages detailles (quel document, quel probleme) pour que le pro ou le client puisse corriger.

### 3.5 Diagnostic
Une fois tous les documents presents et lisibles, le systeme produit un diagnostic **binaire** :
- **VERT** : tous les documents presents, lisibles, coherents → le Cerfa peut etre genere
- **ROUGE** : blocage detecte (document manquant, illisible, incoherence, permis insuffisant) → corrections requises

Il n'y a pas d'etat intermediaire. Toutes les verifications sont faites en temps reel dans la checklist — quand la checklist est 100% verte des deux cotes (vendeur + client), le diagnostic est VERT et le Cerfa se genere.

Verifications effectuees :
- VIN coherent entre tous les documents
- Nom coherent CNI ↔ domicile
- CNI non expiree
- CG barree correctement (VO)
- Kbis present si personne morale
- Permis present (sauf personne morale)

---

## 4. Generation du Cerfa, Signatures et Mandat

### 4.1 Processus
Quand le diagnostic est VERT :
1. Le systeme construit les donnees a partir de tous les documents extraits
2. **Playwright** ouvre le formulaire officiel sur service-public.gouv.fr
3. Remplit automatiquement tous les champs (vehicule, titulaire, adresse)
4. Le site genere le Cerfa PDF officiel
5. Le systeme telecharge le PDF et le stocke dans le dossier
6. Le systeme appose le cachet/signature du pro sur les documents concernes (voir 4.6)

### 4.2 Cerfa VN (13749)
4 etapes sur le site :
1. Identification du vehicule (D.1 a V.9, couleur)
2. Certificat de vente — **pre-rempli automatiquement** a partir de la facture d'achat (voir 4.7)
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

### 4.5 Regles de signature selon le type de transaction

Le pro etant toujours le vendeur, il soumet la demande d'immatriculation en tant que **"professionnel de l'automobile"** — pas besoin de mandat du client.

**Regle cle : pro vendeur ≠ mandataire.** Le mandat 13757 n'est necessaire que si quelqu'un agit au nom du client sans etre le vendeur (hors perimetre actuel).

**Matrice des signatures :**

| Transaction | Document | Signature pro (auto) | Signature client | Remarque |
|-------------|----------|:--------------------:|:----------------:|----------|
| **VN** | Facture d'achat | Oui (cachet) | Non | Cachet auto |
| **VN** | Cerfa 13749 (demande immat.) | Oui (professionnel vendeur) | **Non** | Pro soumet en son nom |
| **VO** | CG barree | Oui | Non | Pro = ancien titulaire |
| **VO** | Cerfa 13750 (demande immat.) | Oui (professionnel vendeur) | **Non** | Pro soumet en son nom |
| **VO** | Cession 15776 (cote vendeur) | Oui | Non | Cachet + signature auto |
| **VO** | Cession 15776 (cote acquereur) | Non | **Oui (numerique)** | Seul doc signe par le client |
| **VO** | Cession 15776 (co-titulaire acquereur) | Non | **Oui (numerique)** | Si co-titulaire renseigne |

**Resultat :**
- **VN sans co-titulaire : zero signature client.**
- **VN avec co-titulaire : zero signature client.** Le co-titulaire fournit ses docs (CNI, permis) mais ne signe rien.
- **VO sans co-titulaire : une seule signature client** — cession 15776 (acquereur).
- **VO avec co-titulaire : deux signatures client** — cession 15776 (acquereur + co-acquereur). Chacun recoit son propre lien SMS.

### 4.6 Signature numerique de la cession (VO uniquement)

En VO, le client doit signer la cession 15776 en tant qu'acquereur. Cette signature est 100% numerique :

**Parcours :**
1. Le pro cree le dossier VO → le systeme genere la cession 15776 pre-remplie
2. Le client recoit un **SMS avec lien securise**
3. Il ouvre la cession dans son navigateur, verifie ses infos
4. Il **signe au doigt/stylet** sur l'ecran (canvas HTML)
5. Il recoit un **code OTP par SMS** et le saisit pour confirmer
6. Le systeme genere le PDF final avec : signature + horodatage + adresse IP + confirmation OTP

**Preuve conservee :** trace signature (PNG) + horodatage + IP + mention "confirme par OTP au 06XX le JJ/MM a HH:MM"

**Cout :** ~0.03-0.05 EUR par dossier (envoi SMS OTP uniquement)

**Co-titulaire :** si un co-titulaire est renseigne, il recoit son propre SMS et signe separement comme co-acquereur. Le systeme attend les deux signatures avant de finaliser la cession.

**Note :** en VN, ce parcours n'est pas declenche — aucune signature client requise (meme avec co-titulaire).

### 4.7 Cachet et signature automatique du pro

**Parametrage initial (une seule fois) :**
Lors de la creation de son espace, le pro uploade :
- Une **photo de sa signature** sur fond blanc
- Une **photo de son cachet** (tampon commercial) sur fond blanc

Les images sont stockees dans son profil (S3, chiffrees).

**Apposition automatique :**
Apres generation de chaque document PDF, le systeme appose le cachet/signature du pro aux emplacements prevus (overlay PDF).

Le systeme determine automatiquement quels documents cacheter/signer selon le type de dossier :
- **VN** : facture + Cerfa 13749
- **VO** : CG barree + cession (cote vendeur) + Cerfa 13750

**Resultat :** zero impression, zero scan, zero signature papier.

### 4.8 Extraction facture → certificat de vente VN

Pour les VN, le systeme extrait automatiquement de la facture d'achat les donnees necessaires au certificat de vente du Cerfa 13749 :
- Identite vendeur (raison sociale, SIRET, adresse du pro)
- Identite acheteur (nom, prenom, adresse du client)
- Donnees vehicule (marque, modele, VIN, date 1ere immatriculation)
- Prix de vente TTC, date de la transaction

Ces donnees sont injectees dans l'etape 2 du formulaire service-public.gouv.fr (certificat de vente), eliminant le remplissage manuel par le pro.

### 4.9 Integration HistoVec (post-habilitation)

**Actuellement :** le pro consulte manuellement HistoVec et uploade le rapport PDF (2 min).

**Evolution prevue** (apres obtention habilitation SIV) :
1. Lors du parametrage de l'espace pro, le vendeur renseigne ses identifiants HistoVec (stockes chiffres)
2. Le systeme interroge automatiquement HistoVec avec le numero d'immatriculation et le numero de formule
3. Le rapport (gage, OTCI, vol, VEC/VEI) est recupere et integre au dossier sans intervention du pro

**Note :** necessite de verifier si l'acces pro habilite SIV donne un acces programmatique ou s'il faut passer par l'extension navigateur.

---

## 5. Espace Admin

Apres generation du Cerfa, l'espace admin affiche :

### 5.1 Vue dossier
- Reference du dossier
- Type (VN/VO)
- Diagnostic (VERT / ROUGE)
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
- Renseigne par le vendeur a la creation du dossier (nom, prenom, telephone, email)
- Le co-titulaire recoit son propre lien d'upload pour deposer ses documents (CNI, permis)
- Multi-propriete cochee automatiquement sur le Cerfa
- **VN** : le co-titulaire fournit ses documents mais ne signe rien
- **VO** : le co-titulaire doit aussi signer la cession 15776 en tant que co-acquereur (signature numerique doigt + OTP via son propre lien SMS)
- Le systeme ne genere le Cerfa que lorsque TOUS les co-titulaires ont fourni leurs documents (et signe la cession en VO)

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

## 8. Mentions Legales, CGU et Securite Juridique

Le systeme integre des mentions legales a chaque niveau pour proteger Imatra, le vendeur pro et le client.

### 8.1 Mentions affichees au client (page upload)

| Mention | Contenu |
|---|---|
| **Authenticite** | "En deposant vos documents, vous certifiez qu'ils sont authentiques. La fourniture de faux documents est un delit (art. 441-1 Code penal)." |
| **Exactitude** | "Vous certifiez que les informations sont exactes et a jour." |
| **Role du service** | "Imatra est un outil d'aide, pas un conseiller juridique ni un substitut de l'administration." |
| **Responsabilite** | "La soumission est effectuee par [vendeur] sous sa responsabilite. Imatra ne garantit pas l'acceptation par le SIV." |
| **Conservation** | "Documents supprimes a la finalisation du dossier." |

Ces mentions sont affichees sur la page d'upload **avant** le consentement RGPD.

### 8.2 Mentions affichees au vendeur pro (espace admin)

| Mention | Contenu |
|---|---|
| **Responsabilite soumission** | "En tant que pro habilite SIV, vous restez seul responsable de la veracite du dossier soumis." |
| **Verification OCR** | "Les donnees extraites automatiquement peuvent contenir des erreurs. Verifiez avant soumission." |
| **Estimation taxes** | "Montants indicatifs. Le montant definitif est determine par le SIV." |
| **Conservation** | "Dossiers archives 5 ans conformement a la reglementation." |
| **Limitation responsabilite** | "Imatra ne garantit pas l'acceptation du dossier. Honoraires non remboursables si rejet du a des documents incorrects." |

Ces mentions sont affichees dans le **recapitulatif de validation** avant envoi du lien client.

### 8.3 CGU / CGV (accessibles via /api/mentions-legales)

**Limitation de responsabilite :**
- Imatra = outil d'aide, pas mandataire, pas conseiller juridique
- Pas de garantie d'acceptation SIV
- OCR approximatif — le pro doit verifier
- Estimations taxes indicatives
- Infos reglementaires a titre informatif
- Pas de responsabilite en cas d'indisponibilite SIV ou services tiers

**Responsabilites du pro :**
- Veracite et completude du dossier soumis
- Verification des donnees extraites
- Authenticite des documents clients

**Responsabilites du client :**
- Authenticite des documents (delit penal si faux)
- Exactitude des informations

**CGV :**
- Tarif fixe : 12 EUR moto / 14 EUR voiture par dossier
- Paiement par batch de 5 dossiers
- Non remboursable si rejet du a documents incorrects
- Remboursement si dysfonctionnement du service

**Donnees personnelles :**
- Documents client supprimes a la finalisation
- Dossiers pro archives 5 ans
- Donnees facturation archives 10 ans
- Contact DPO : rgpd@cartegrisepro.fr

---

## 9. Endpoints API

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
