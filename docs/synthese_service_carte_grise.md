# Synthese du Service Carte Grise — Analyse Complete

## 1. Le Service en Bref

**Carte Grise Pro** est un outil integre dans le site d'un commercant moto qui automatise la demande de carte grise (VN et VO). Le pro depose ses documents vehicule dans son espace admin, le client recoit automatiquement un lien pour uploader ses documents d'identite — pas d'espace client, pas de compte a creer. Le systeme verifie, extrait, diagnostique, genere le Cerfa officiel pre-rempli, appose le cachet/signature du pro automatiquement, et gere la signature numerique de la cession (VO).

**Perimetre :** Motos + Voitures | VN + VO | Personne physique + morale | Co-titulaire

---

## 2. Parcours Complet — Ce que fait chaque acteur

### 2.1 Ce que fait le PRO (vendeur / commercant moto)

| Etape | Action du pro | Temps estime |
|-------|--------------|-------------|
| 1 | Cree le dossier (VN/VO, infos client, VIN/immat) | 30 sec |
| 2 | Depose le COC dans son espace admin | 15 sec |
| 3 | Depose la facture de vente (VN) ou CG barree (VO) | 15 sec |
| 4 | → Le systeme envoie automatiquement un lien au client | — |
| 5 | Attend que le client uploade ses docs via le lien | — |
| 6 | Verifie le diagnostic VERT/ORANGE/ROUGE | 10 sec |
| 7 | Lance la generation du Cerfa (1 clic) | 15-45 sec (auto) |
| 8 | Verifie les messages admin (attestation formation, assurance) | 30 sec |
| 9 | Recupere les Cerfa signes/cachetes automatiquement | — |
| 10 | Soumet au SIV | — |
| 11 | Facture le client (prix libre) | 1 min |

**Temps total pro : ~5 minutes**

### 2.2 Ce que fait le CLIENT (acheteur)

**Pas d'espace client sur le site du commercant.** Le client recoit automatiquement un lien securise (SMS/email) vers une page d'upload simple — pas de compte, pas de login.

| Etape | Ce que fait le client | Temps estime |
|-------|----------------------|-------------|
| 1 | Recoit un lien automatique apres depot des docs pro | — |
| 2 | Uploade CNI, permis, justificatif domicile via le lien | 2 min |
| 3 | Uploade attestation formation (si moto 125cc) | 15 sec |
| 4 | (VO uniquement) Signe la cession 15776 au doigt + OTP SMS | 30 sec |

**Temps total client : ~2-3 minutes** (VN = upload docs seulement | VO = upload + signature cession 30 sec)

### 2.3 Ce que fait le SYSTEME (automatique)

| Etape | Action automatique | Temps |
|-------|-------------------|-------|
| 1 | Envoi automatique du lien client apres depot docs pro | instantane |
| 2 | OCR sur chaque document (Tesseract local + Google DocAI fallback) | 1-5 sec/doc |
| 3 | Classification automatique (9 types de documents) | instantane |
| 4 | Extraction des donnees (nom, VIN, adresse, dates, etc.) | instantane |
| 5 | Extraction facture → pre-remplissage certificat de vente VN | instantane |
| 6 | Fusion recto/verso si meme type uploade 2 fois | instantane |
| 7 | Anti-doublon (remplacement si re-upload) | instantane |
| 8 | Detection auto personne morale (si Kbis present) | instantane |
| 9 | Verification coherence VIN entre documents | instantane |
| 10 | Verification coherence nom CNI ↔ domicile | instantane |
| 11 | Verification CNI non expiree | instantane |
| 12 | Verification CG barree + signatures (VO) | instantane |
| 13 | Diagnostic VERT/ORANGE/ROUGE | instantane |
| 14 | Estimation des taxes (Y1-Y6) | instantane |
| 15 | Generation Cerfa via Playwright (service-public.gouv.fr) | 15-45 sec |
| 16 | Apposition cachet/signature du pro sur les documents | instantane |
| 17 | (VO) Envoi lien signature cession au client + co-titulaire | instantane |
| 18 | Stockage Cerfa dans l'espace admin | instantane |
| 19 | Messages admin (attestation formation, assurance) | instantane |
| 20 | Suivi : ajout au compteur dossiers (max 5), generation demande de paiement | instantane |

---

## 3. Comparatif — Ce que fait le pro aujourd'hui sans notre systeme

Un vendeur pro habilite SIV a aujourd'hui 3 options pour gerer la carte grise de son client :

### 3.1 Les 3 options actuelles du pro

#### Option A — Le pro fait tout lui-meme via son acces SIV

1. Collecte les documents du client (CNI, permis, domicile, etc.)
2. Verifie manuellement la coherence (VIN, noms, dates, expiration)
3. Remplit le Cerfa a la main ou sur service-public.gouv.fr (15-20 champs)
4. Imprime, appose son cachet, fait signer le client
5. Soumet au SIV via son portail habilite
6. Gere les corrections si erreur de saisie

**Temps : ~30 minutes par dossier**
**Revenu : le pro peut facturer le service (20-50 EUR) mais perd 30 min de temps de vente**
**Risque : erreurs de saisie, oubli de document, rejet SIV**

#### Option B — Le pro envoie le client se debrouiller

Le pro dit au client d'aller sur Cartegrise.com, Eplaque.fr ou ANTS.

| Service externe | Prix client | Temps client | Revenu pro |
|----------------|-------------|-------------|------------|
| Cartegrise.com | 29.90 EUR + taxes | 15-30 min | **0 EUR** |
| Eplaque.fr | 24.90 EUR + taxes | 15-30 min | **0 EUR** |
| LegalPlace | 29.90 EUR + taxes | 15-30 min | **0 EUR** |
| ANTS (direct) | 0 EUR | 30+ min | **0 EUR** |

**Temps pro : 0 min**
**Revenu pro : 0 EUR — le client paie un tiers, le pro ne gagne rien**
**Probleme : le client quitte le site du pro, mauvaise experience, pas de fidelisation**

#### Option C — Le pro utilise notre systeme

1. Depose ses docs vehicule (30 sec)
2. Le client recoit un lien et uploade ses docs (2-3 min)
3. Le systeme verifie, extrait, genere le Cerfa, appose cachet/signature (automatique)
4. Le pro soumet au SIV avec un dossier complet et verifie
5. Le pro facture son client (prix libre)

**Temps pro : ~5 minutes**
**Revenu pro : tout ce qu'il facture au client minus notre tarif fixe (~12 EUR moto, ~14 EUR voiture)**
**Risque : quasi nul — le systeme detecte les erreurs avant soumission SIV**

### 3.2 Comparatif des 3 options

| | Option A (pro fait tout) | Option B (service externe) | **Option C (notre systeme)** |
|---|---|---|---|
| Temps pro | 30 min | 0 min | **5 min** |
| Saisie manuelle | Oui (15-20 champs) | Non (le client fait) | **Non (extraction auto)** |
| Verification documents | Manuelle | Faite par le tiers | **Automatique (VIN, nom, dates, CNI)** |
| Cerfa | Rempli a la main | Fait par le tiers | **Genere en 1 clic** |
| Cachet/signature | Imprimer + tamponner + scanner | — | **Automatique** |
| Signature client (VN) | Oui | Oui | **Non (pro = vendeur pro)** |
| Signature client (VO) | Imprimer + signer + scanner | Idem | **Doigt + OTP SMS (30 sec)** |
| Risque erreur SIV | Eleve (saisie manuelle) | Faible (le tiers gere) | **Faible (diagnostic auto avant soumission)** |
| Le client reste chez le pro | Oui | Non | **Oui** |
| Le pro facture le client | Oui (mais 30 min de travail) | Non (le tiers facture) | **Oui (5 min de travail)** |
| **Revenu pro** | **20-50 EUR mais 30 min perdues** | **0 EUR** | **Prix libre - 12 EUR (notre tarif)** |

### 3.3 Fonctionnalites detaillees vs saisie manuelle

| Fonctionnalite | Pro fait a la main | Notre systeme |
|---------------|-------------------|---------------|
| OCR des documents | Non — lecture visuelle | Tesseract + Google DocAI |
| Extraction donnees | Recopie manuelle | Automatique (regex + IA) |
| Certificat de vente VN | Remplissage manuel | Pre-rempli depuis la facture d'achat |
| Coherence inter-documents | Verification visuelle | Croisement auto (VIN, nom, dates) |
| CNI expiree | Le pro doit verifier | Detection automatique |
| CG barree correctement (VO) | Le pro doit verifier | Detection automatique |
| Fusion recto/verso | Le pro assemble | Automatique |
| Detection personne morale | Le pro identifie | Automatique (si Kbis) |
| Estimation taxes | Le pro calcule ou devine | Automatique (Y1-Y6) |
| Collecte docs client | Le pro relance par tel/email | Lien automatique SMS/email |
| Gestion co-titulaire | Le pro gere manuellement | Lien + signature separee auto |
| Suivi facturation | Le pro gere dans sa compta | Tableau de bord integre |

### 3.4 Nos Avantages

#### Pour le pro (commercant moto)

**Liberte tarifaire totale — l'avantage concurrentiel majeur :**

Le pro fixe **librement** son prix au client. Notre tarif reste le meme : **12 EUR (moto) / 14 EUR (voiture)**, base sur 50% de la facturation de reference competitive (marche -20%). Ce que le pro facture a son client ne change rien a ce qu'il nous doit.

**Les 4 leviers du pro :**

| Levier | Strategie du pro | Prix client | Notre tarif (fixe) | Marge pro | Avantage |
|--------|-----------------|-------------|-------------------|-----------|----------|
| **Casser les prix** | Facturer moins cher que le marche | 15-20 EUR | 12 EUR | 3-8 EUR | Attirer des clients, se differencier des concurrents en ligne |
| **Prix competitif** | S'aligner sur le prix de reference | 24 EUR | 12 EUR | 12 EUR | Partenariat 50/50 exact, client paie 20% de moins que le marche |
| **Prix marche** | Facturer comme les concurrents | 30 EUR | 12 EUR | 18 EUR | Maximiser la marge par dossier |
| **Offrir le service** | Inclure dans le prix du vehicule | 0 EUR (offert) | 12 EUR | -12 EUR (absorbe) | Argument de vente : "carte grise offerte", fidelisation |

**Aucun autre systeme ne permet ca.** Les services externes (Cartegrise.com, Eplaque) facturent le client directement a 25-40 EUR. Le pro n'a aucun controle sur le prix, aucun revenu, aucun levier commercial.

**Source de revenu vs les alternatives actuelles :**
- **Option A (tout a la main)** : le pro peut facturer mais perd 30 min → avec nous, meme revenu en 5 min
- **Option B (service externe)** : le pro gagne 0 EUR, n'a aucun levier → avec nous, il controle tout
- **Zero investissement** — pas de forfait, pas d'abonnement, pas de mise de depart
- **Zero risque financier** — il obtient le Cerfa, facture son client, puis paie notre tarif fixe
- **Fidilisation client** — le service carte grise devient un argument de vente, le client reste chez le pro

**Gain de temps :**
- **5 minutes par dossier** au lieu de 30 min de saisie manuelle via SIV
- **Zero saisie** — le systeme extrait tout des documents, le pro ne remplit aucun formulaire
- **Cerfa genere en 1 clic** — plus d'erreurs de remplissage, plus de corrections, plus de rejets SIV
- **Cachet/signature apposes automatiquement** — photo uploadee une fois au parametrage, reutilisee a vie
- **Certificat de vente VN pre-rempli** — extraction auto depuis la facture d'achat
- **HistoVec automatise** apres habilitation SIV — plus de copier-coller manuel
- **Collecte docs client automatisee** — le systeme envoie le lien, le client uploade, le pro n'a rien a faire

**Fiabilite :**
- **Diagnostic avant soumission SIV** — document manquant, VIN incoherent, CNI expiree detectes en amont
- **Zero erreur de saisie** — tout est extrait automatiquement, pas de recopie manuelle
- **Verification coherence inter-documents** — le systeme croise VIN, noms, dates entre tous les docs
- **Le pro soumet au SIV avec un dossier verifie** — moins de rejets, moins de corrections

**Simplicite :**
- **Integre dans son site** — pas de redirection, pas de site externe
- **Tableau de bord** — compteur dossiers, solde a payer, historique
- **Aucune competence technique requise** — le systeme fait le travail
- **Gestion moto specifique** — attestation formation 125cc/L5e, CT moto

#### Pour le client (acheteur)

**Potentiellement moins cher :**
- **Le pro fixe le prix** — il peut proposer un tarif inferieur aux services en ligne (25-40 EUR)
- **Le pro peut meme offrir le service** en l'incluant dans le prix de vente du vehicule
- **Prix transparent** — pas de frais caches, pas de supplement

**Plus simple :**
- **Rien a comprendre** — il recoit un lien, uploade ses documents, c'est fini
- **Pas de compte a creer, pas de login** — un simple lien securise
- **Pas de formulaire a remplir** — le systeme extrait tout des documents
- **Liste claire** des documents a fournir, adaptee au type de dossier
- **Fait directement chez son commercant** — pas besoin d'aller sur un site inconnu

**Plus rapide :**
- **2-3 minutes** au lieu de 15-30 min sur les sites en ligne
- **VN : zero signature** — le pro gere tout comme vendeur professionnel
- **VO : 30 secondes** — une seule signature (cession au doigt + OTP SMS)
- **100% numerique** — zero impression, zero scan, zero deplacement

#### Pour nous (plateforme)

**Modele economique :**
- **Tarif fixe par dossier** base sur partenariat 50/50 (prix de reference marche -20%)
- **12 EUR par dossier moto**, 14 EUR par dossier voiture — simple, previsible
- **Marge nette > 98%** — cout reel ~0.20 EUR/dossier
- **Revenus recurrents** — les pros traitent des dossiers chaque mois

**Scalabilite :**
- **50 pros × 25 dossiers/mois = 15 000 dossiers/an = ~180 000 EUR/an** (a 12 EUR/dossier moto)
- **100 pros = ~360 000 EUR/an** pour un cout infrastructure de ~2 000 EUR/an
- Chaque nouveau pro ajoute du revenu recurrent sans cout marginal significatif

**Protection :**
- **Verrou paiement** — le pro doit payer les dossiers en cours (max 5) avant de continuer
- **Stickiness forte** — une fois integre dans le site du pro, le cout de changement est eleve
- **Zero service client** — le pro gere la relation avec son client, on fournit l'outil
- **Donnees marche** — visibilite sur les volumes de carte grise par type, zone, saisonnalite

### 3.5 Nos Limites (transparence)

| Limite | Impact | Mitigation |
|--------|--------|-----------|
| Pas de soumission SIV | Le pro soumet lui-meme au SIV | Cerfa pre-rempli + cachet/signature = 95% du travail fait |
| OCR Tesseract limite sur photos sombres | Fallback Google DocAI (payant ~0.01 EUR/page) | Le systeme bascule automatiquement |
| Pas de paiement taxes integre | En attente reponse ANTS | Le pro gere les taxes dans son SIV |

---

## 4. Modele Economique

### 4.1 Couts reels du systeme

| Poste | Cout | Frequence |
|-------|------|-----------|
| Tesseract OCR | Gratuit | Illimite |
| Google DocAI (fallback) | ~0.01 EUR/page | ~20% des dossiers |
| Playwright (generation Cerfa) | Gratuit | Illimite |
| SMS OTP (signature cession VO) | ~0.03-0.05 EUR | VO uniquement |
| SMS lien client | ~0.03 EUR | 1 par dossier |
| Hebergement serveur | 10-30 EUR/mois | Fixe |
| **Cout reel par dossier** | **~0.10-0.25 EUR** | |

### 4.2 Modele de facturation : partenariat 50/50

**Comment on calcule notre tarif :**

1. On prend le **prix moyen du marche** (ce que les concurrents facturent au client final)
2. On applique **-20%** pour obtenir un prix de reference competitif
3. On partage ce prix de reference **50/50** entre nous et le pro

```
Prix marche moyen → -20% → prix de reference → 50% nous / 50% pro
```

**Calcul detaille :**

| Etape | Moto | Voiture |
|-------|------|---------|
| Prix marche moyen (Cartegrise.com, Eplaque, etc.) | ~30 EUR | ~35 EUR |
| Prix de reference (-20%) | 24 EUR | 28 EUR |
| **Notre tarif (50% du prix de reference)** | **12 EUR** | **14 EUR** |
| Part pro (50% du prix de reference) | 12 EUR | 14 EUR |

**Notre tarif est fixe par dossier : 12 EUR (moto) / 14 EUR (voiture).** C'est ce que le pro nous paie, quel que soit le prix qu'il facture a son client.

**Le pro fixe librement son prix au client.** Tout ce qu'il facture au-dessus de notre tarif, il le garde a 100% :
- Si le pro facture 20 EUR → il garde 20 - 12 = **8 EUR** (et le client paie 33% moins cher que le marche)
- Si le pro facture 24 EUR → il garde 24 - 12 = **12 EUR** (partenariat 50/50 exact)
- Si le pro facture 30 EUR → il garde 30 - 12 = **18 EUR**
- Si le pro inclut dans la vente → il absorbe 12 EUR dans sa marge vehicule

Plus le pro facture, plus il gagne. Notre tarif ne change pas.

### 4.3 Flux financier et verrou de paiement

**Le pro peut traiter jusqu'a 5 dossiers en batch.** Il obtient les Cerfa, soumet au SIV, facture ses clients. Mais il doit **payer notre tarif avant de pouvoir traiter de nouveaux dossiers**.

```
Pro uploade jusqu'a 5 dossiers → Systeme genere les Cerfa
    → Pro soumet au SIV, facture ses clients (prix libre)
        → Pro paie notre tarif (5 × 12 EUR = 60 EUR pour 5 motos)
            → Systeme debloque → Pro peut traiter 5 nouveaux dossiers
```

1. Le pro uploade et traite **jusqu'a 5 dossiers** en une fois
2. Le systeme genere les Cerfa (cachet/signature auto)
3. Le pro soumet au SIV et facture ses clients au prix de son choix
4. **Le pro paie notre tarif** pour les dossiers traites (CB, virement ou prelevement SEPA)
5. Le systeme se debloque → le pro peut traiter 5 nouveaux dossiers

**Verrou : tant que le pro n'a pas paye les dossiers en cours, le systeme ne genere plus de nouveau Cerfa.**

| Situation | Consequence |
|-----------|------------|
| Pro a traite 1 a 5 dossiers | Cerfa generes, pro peut soumettre au SIV |
| Pro veut traiter un 6eme dossier | **Systeme bloque** — paiement des dossiers en cours requis |
| Pro paie son solde | Systeme debloque — 5 nouveaux dossiers disponibles |

### 4.4 Tableau de bord du pro

Le pro dispose d'un tableau de bord dans son espace admin :

- **Dossiers en cours** : X/5 (compteur visuel)
- **Solde a payer** : montant total des dossiers traites non regles
- **Historique** : tous les dossiers traites, dates, montants payes
- **Export** : telechargement CSV/PDF pour la comptabilite du pro

### 4.5 Exemple mensuel

Pour un commercant moto qui traite **25 dossiers/mois** :

| | Montant |
|---|---|
| Notre tarif fixe | 25 × 12 = **300 EUR** |
| Si le pro facture 24 EUR/dossier | Encaisse 600 - 300 = **marge 300 EUR** |
| Si le pro facture 30 EUR/dossier | Encaisse 750 - 300 = **marge 450 EUR** |
| Si le pro inclut dans la vente | Absorbe 300 EUR dans marge vehicule |
| Temps de travail pro | ~2h (25 × 5 min) |

### 4.6 Comparatif final

| | Concurrent (Cartegrise.com) | ANTS direct | **Notre systeme** |
|---|---|---|---|
| Prix client | 29.90 EUR | 0 EUR (mais 30 min de travail) | **Libre (fixe par le pro)** |
| Travail pro | 0 min (il n'intervient pas) | 30 min saisie manuelle | **5 min** |
| Notre tarif | — | — | **Fixe (12 EUR moto / 14 EUR voiture)** |
| Revenu pro | 0 EUR | 0 EUR | **Prix client - 12 EUR** |
| Investissement pro | — | — | **0 EUR (paie par dossier)** |
| Le client reste chez le pro | Non | Non | **Oui** |

---

## 5. Experience Utilisateur Comparee

### 5.1 Le pro fait tout a la main (option A — aujourd'hui)

1. Le client arrive en magasin, le pro lui demande CNI, permis, domicile
2. Le pro photocopie/scanne les documents
3. Le pro verifie visuellement : VIN, noms, dates d'expiration
4. Le pro ouvre service-public.gouv.fr et remplit 15-20 champs a la main
5. Le pro imprime le Cerfa, appose son cachet, fait signer le client
6. Le pro soumet au SIV via son portail
7. Si erreur → correction → re-soumission

**Resultat :** 30 min de travail, risque d'erreur, le pro facture 20-50 EUR mais perd du temps de vente.

### 5.2 Le client va sur un site externe (option B — aujourd'hui)

1. Le pro dit au client "allez sur cartegrise.com"
2. Le client quitte le site du commercant
3. Le client remplit un formulaire de 15-20 champs
4. Le client paie 29.90 EUR a un tiers
5. Le pro ne gagne rien, ne controle rien

**Resultat :** 0 min de travail pro, 0 EUR de revenu pro, le client part ailleurs.

### 5.3 Avec notre systeme (option C)

1. Le pro cree le dossier en 30 sec et depose ses docs
2. Le client recoit un lien automatique et uploade ses docs en 2-3 min
3. Le systeme verifie, extrait, diagnostique automatiquement
4. Le pro genere le Cerfa en 1 clic (15-45 sec)
5. Cachet/signature apposes automatiquement
6. (VO) Le client signe la cession au doigt + OTP — 30 sec
7. Le pro soumet au SIV avec un dossier complet et verifie
8. Le pro facture le client au prix de son choix
9. Le pro paie notre tarif fixe (12 ou 14 EUR) pour debloquer de nouveaux dossiers

**Resultat :** 5 min de travail pro, 2-3 min cote client. Le client reste sur le site du commercant. Le pro facture ce qu'il veut et garde tout au-dessus de notre tarif fixe. Zero risque d'erreur SIV grace au diagnostic automatique.

---

## 6. Fonctionnalites Detaillees

### Documents acceptes et traites
- CNI / Passeport (recto + verso, fusion auto)
- Permis de conduire (recto + verso)
- Justificatif de domicile (facture EDF/Engie/TotalEnergies, etc.)
- COC (Certificat de Conformite constructeur)
- Carte grise barree (extraction 25 champs, verification signature/barre)
- Facture de vente (extraction pour certificat de vente VN)
- Kbis (detection auto personne morale)
- Attestation de formation moto 125cc/L5e
- Attestation d'assurance (optionnel)
- Rapport HistoVec (VO — automatise apres habilitation SIV)
- Cession 15776 (VO — generee et signee numeriquement)

### Verifications automatiques
- VIN coherent entre tous les documents
- Nom coherent CNI ↔ justificatif domicile
- CNI non expiree (regle +5 ans 2004-2013)
- CG barree correctement + signatures co-titulaires (VO)
- Cession signee vendeur + acquereur (VO)
- Kbis present si personne morale
- Permis present (sauf personne morale)
- Documents obligatoires presents selon le type (VN/VO)

### Generation Cerfa
- Cerfa 13749 (VN) — tous les champs techniques remplis (D.1 a V.9) + certificat de vente pre-rempli
- Cerfa 13750 (VO) — vehicule + titulaire + case Certificat cochee
- Personne morale : case cochee + SIREN + raison sociale
- Couleur dominante cochee
- Co-titulaire si applicable
- Cachet/signature du pro apposes automatiquement

### Signatures
- **VN** : zero signature client — pro signe comme vendeur professionnel
- **VO** : signature cession 15776 par le client (doigt + OTP SMS)
- **Co-titulaire VO** : chacun recoit son propre lien de signature
- **Cachet/signature pro** : photo uploadee une fois au parametrage, apposee auto sur tous les docs

---

## 7. Conclusion

Notre service se differencie des concurrents sur 5 points cles :

1. **Rapidite** — 5 min pro + 2-3 min client. Cerfa genere en 30 sec, cachet/signature auto.
2. **Facilite** — zero saisie manuelle, zero formulaire. Le client uploade via un lien, le systeme fait le reste.
3. **100% numerique** — signature cession au doigt (VO), cachet pro auto, zero papier, zero impression.
4. **Integre** — dans le site du commercant, pas de redirection, le client reste chez le pro.
5. **Partenariat 50/50** — tarif fixe (12 EUR moto / 14 EUR voiture), le pro fixe son prix librement et garde tout au-dessus. Plus il facture, plus il gagne.

Le commercant moto transforme un service administratif penible en **source de revenu** avec un partenariat simple et transparent : 12 EUR par dossier moto, le pro facture ce qu'il veut a son client. A 25 dossiers par mois, c'est 300 EUR pour la plateforme et au minimum 300 EUR de marge pour le pro — pour 2h de travail total.
