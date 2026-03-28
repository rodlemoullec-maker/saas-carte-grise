# Synthese du Service Carte Grise — Analyse Complete

## 1. Le Service en Bref

**Carte Grise Pro** est un outil integre dans le site d'un commercant moto qui automatise la generation du Cerfa de demande d'immatriculation (VN et VO). Le pro et le client deposent chacun leurs documents dans un espace dedie, le systeme verifie, extrait les donnees, et genere le Cerfa officiel pre-rempli via le site service-public.gouv.fr.

**Perimetre actuel :** Motos + Voitures | VN + VO | Personne physique + morale

---

## 2. Parcours Complet — Ce que fait chaque acteur

### 2.1 Ce que fait le PRO (vendeur / commercant moto)

| Etape | Action du pro | Temps estime |
|-------|--------------|-------------|
| 1 | Cree le dossier (VN/VO, infos client, VIN/immat) | 30 sec |
| 2 | Depose le COC dans l'espace vendeur | 15 sec |
| 3 | Depose la facture de vente (VN) | 15 sec |
| 4 | Consulte HistoVec et uploade le rapport PDF (VO) | 2 min |
| 5 | Attend que le client depose ses documents | — |
| 6 | Verifie le diagnostic VERT/ORANGE/ROUGE | 10 sec |
| 7 | Lance la generation du Cerfa (1 clic) | 15-45 sec (auto) |
| 8 | (Optionnel) Lance la signature : telecharge le Cerfa, signe, re-uploade | 2 min |
| 9 | Verifie les messages admin (attestation formation, assurance) | 30 sec |
| 10 | Recupere le Cerfa signe complet dans l'espace admin | — |

**Temps total pro : ~5-8 minutes** (dont 2 min HistoVec)

### 2.2 Ce que fait le CLIENT (acheteur)

| Etape | Action du client | Temps estime |
|-------|-----------------|-------------|
| 1 | Se connecte a l'espace client (lien envoye par le pro) | 10 sec |
| 2 | Voit la liste des documents a deposer | — |
| 3 | Uploade CNI (recto + verso) | 20 sec |
| 4 | Uploade permis de conduire (recto + verso) | 20 sec |
| 5 | Uploade justificatif de domicile | 15 sec |
| 6 | Uploade carte grise barree (VO) | 15 sec |
| 7 | Uploade attestation formation moto (si 125cc/L5e) | 15 sec |
| 8 | Uploade attestation assurance (optionnel) | 15 sec |
| 9 | (Si signature lancee) Telecharge le Cerfa signe vendeur, signe, re-uploade | 2 min |

**Temps total client : ~3-5 minutes**

### 2.3 Ce que fait le SYSTEME (automatique)

| Etape | Action automatique | Temps |
|-------|-------------------|-------|
| 1 | OCR sur chaque document (Tesseract local + Google DocAI fallback) | 1-5 sec/doc |
| 2 | Classification automatique (9 types de documents) | instantane |
| 3 | Extraction des donnees (nom, VIN, adresse, dates, etc.) | instantane |
| 4 | Fusion recto/verso si meme type uploade 2 fois | instantane |
| 5 | Anti-doublon (remplacement si re-upload) | instantane |
| 6 | Detection auto personne morale (si Kbis present) | instantane |
| 7 | Diagnostic VERT/ORANGE/ROUGE | instantane |
| 8 | Verification coherence VIN entre documents | instantane |
| 9 | Verification coherence nom CNI ↔ domicile | instantane |
| 10 | Verification CNI non expiree | instantane |
| 11 | Verification CG barree (VO) | instantane |
| 12 | Estimation des taxes (Y1-Y6) | instantane |
| 13 | Generation Cerfa via Playwright (service-public.gouv.fr) | 15-45 sec |
| 14 | Case Certificat cochee automatiquement (VO) | inclus |
| 15 | Stockage Cerfa dans l'espace admin | instantane |
| 16 | Messages admin (attestation formation, assurance) | instantane |

---

## 3. Comparatif avec les Concurrents

### 3.1 Nos concurrents

| Concurrent | Modele | Prix | Cible |
|-----------|--------|------|-------|
| **Cartegrise.com** | Full service en ligne | 29.90 EUR + taxes | Particuliers |
| **Eplaque.fr** | Full service en ligne | 24.90 EUR + taxes | Particuliers |
| **LegalPlace** | Full service en ligne | 29.90 EUR + taxes | Particuliers + pros |
| **Mon Immatriculation** | Full service | 24.90-39.90 EUR + taxes | Particuliers |
| **ANTS (direct)** | Gratuit (self-service) | 0 EUR (taxes seules) | Tous |
| **Prefectures habilitees** | Full service physique | 30-60 EUR + taxes | Tous |

### 3.2 Ce qu'ils font vs ce qu'on fait

| Fonctionnalite | Eux (Cartegrise.com, Eplaque) | Nous |
|---------------|------------------------------|------|
| Le client saisit tout manuellement | Oui — formulaire long | Non — extraction auto des documents |
| OCR des documents | Non | Oui — Tesseract + Google DocAI |
| Verification coherence inter-documents | Non (verification manuelle) | Oui — VIN, nom, dates |
| Cerfa pre-rempli automatiquement | Non (saisie manuelle) | Oui — Playwright via service-public.gouv.fr |
| Espace vendeur + client separes | Non | Oui |
| Fusion recto/verso automatique | Non | Oui |
| Anti-doublon documents | Non | Oui |
| Detection personne morale auto | Non | Oui (si Kbis) |
| Estimation taxes en temps reel | Parfois | Oui |
| Integre dans le site du commercant | Non (site externe) | Oui — integre dans le site moto |
| Support moto specifique (attestation formation) | Non | Oui |
| Cout pour le pro | 0 (il facture au client) | 0 (integre) |
| Cout pour le client | 25-40 EUR + taxes | Honoraires pro (libre) |

### 3.3 Nos Avantages

**Pour le pro (commercant moto) :**
- **Integre dans son site** — pas de redirection vers un site tiers
- **Zero saisie manuelle** — tout est extrait des documents
- **Cerfa officiel genere automatiquement** — plus d'erreurs de remplissage
- **Maitrise des honoraires** — il fixe son prix (pas impose par un intermediaire)
- **Fidilisation client** — le client reste sur le site du commercant
- **Gestion moto specifique** — attestation formation 125cc/L5e geree

**Pour le client (acheteur) :**
- **Simple** — il uploade ses docs et c'est fini
- **Rapide** — 3-5 minutes au lieu de 15-30 min sur les sites concurrents
- **Pas de formulaire a remplir** — le systeme extrait tout
- **Liste claire** des documents a fournir (obligatoires vs optionnels)
- **Pas de re-saisie** — les infos CNI/permis/domicile sont extraites automatiquement

**Techniquement :**
- **OCR dual** — Tesseract gratuit + Google DocAI pour les cas difficiles
- **Cerfa officiel** genere par le site gouvernemental (pas un PDF maison)
- **Coherence inter-documents** verifiee automatiquement
- **Fonctionne pour motos ET voitures, VN ET VO**

### 3.4 Nos Limites (transparence)

| Limite | Impact | Mitigation |
|--------|--------|-----------|
| Pas de soumission SIV | Le pro soumet lui-meme au SIV | Cerfa pre-rempli = 90% du travail fait |
| Certificat de vente VN non rempli | Bug du site service-public.fr | Le pro le remplit a la main (30 sec) |
| OCR Tesseract limite sur photos sombres | Fallback Google DocAI (payant) | Demander des scans propres au client |
| Pas d'acces HistoVec automatique | Le pro uploade le rapport PDF | 2 min de plus pour le pro |
| Signature manuelle (pas electronique) | Impression + scan necessaire | Standard du marche — personne ne fait mieux |
| Pas de paiement taxes integre | En attente reponse ANTS | Le pro gere les taxes dans son SIV |

---

## 4. Modele Economique

### 4.1 Couts du systeme

| Poste | Cout | Frequence |
|-------|------|-----------|
| Tesseract OCR | Gratuit | Illimite |
| Google DocAI (fallback) | ~0.01 EUR/page | Seulement si Tesseract echoue |
| Playwright (generation Cerfa) | Gratuit | Illimite |
| Hebergement serveur | 10-30 EUR/mois | VPS ou cloud |
| **Total par dossier** | **~0.05-0.15 EUR** | |

### 4.2 Comparatif cout

| Solution | Cout par dossier | Marge pro |
|---------|-----------------|-----------|
| Cartegrise.com | 25-40 EUR (facture au client) | 0 pour le pro |
| Eplaque.fr | 25 EUR (facture au client) | 0 pour le pro |
| **Notre systeme** | **~0.10 EUR (cout reel)** | **Le pro fixe ses honoraires** |
| ANTS direct | 0 EUR (mais 30 min de travail) | Temps perdu |

**Le pro peut facturer 20-50 EUR au client et garder 99% de marge** car le cout reel est de quelques centimes par dossier.

---

## 5. Experience Utilisateur Comparee

### 5.1 Chez un concurrent (Cartegrise.com)

1. Le client va sur cartegrise.com
2. Remplit un formulaire de 15-20 champs manuellement
3. Uploade ses documents (CNI, permis, etc.)
4. Paie 29.90 EUR + taxes
5. Attend 3-7 jours pour recevoir la carte grise
6. Le commercant n'est pas implique

**Problemes :** saisie manuelle longue, erreurs frequentes, le client quitte le site du commercant, le pro ne gagne rien.

### 5.2 Chez nous

1. Le pro cree le dossier en 30 sec
2. Le client uploade ses docs en 3 min (pas de formulaire)
3. Le systeme genere le Cerfa en 30 sec
4. Le pro soumet au SIV
5. Le client paie les honoraires au pro (prix libre)

**Avantages :** rapide, zero saisie, le client reste sur le site du commercant, le pro controle l'experience et les honoraires.

---

## 6. Fonctionnalites Detaillees

### Documents acceptes et traites
- CNI / Passeport (recto + verso, fusion auto)
- Permis de conduire (recto + verso)
- Justificatif de domicile (facture EDF/Engie/TotalEnergies, etc.)
- COC (Certificat de Conformite constructeur)
- Carte grise (extraction 25 champs)
- Kbis (detection auto personne morale)
- Attestation de formation moto 125cc/L5e
- Attestation d'assurance (optionnel)
- Rapport HistoVec (VO)
- Facture de vente

### Verifications automatiques
- VIN coherent entre tous les documents
- Nom coherent CNI ↔ justificatif domicile
- CNI non expiree (regle +5 ans 2004-2013)
- CG barree correctement (VO)
- Kbis present si personne morale
- Permis present (sauf personne morale)
- Documents obligatoires presents selon le type (VN/VO)

### Generation Cerfa
- Cerfa 13749 (VN) — tous les champs techniques remplis (D.1 a V.9)
- Cerfa 13750 (VO) — vehicule + titulaire + case Certificat cochee
- Personne morale : case cochee + SIREN + raison sociale
- Couleur dominante cochee
- Co-titulaire si applicable

---

## 7. Conclusion

Notre service se differencie des concurrents sur 3 points cles :

1. **Zero saisie manuelle** — le client uploade, le systeme extrait. Pas de formulaire a remplir.
2. **Integre dans le site du commercant** — le client ne quitte pas le site, le pro controle l'experience.
3. **Cout quasi-nul** — quelques centimes par dossier vs 25-40 EUR chez les concurrents.

Le commercant moto peut proposer le service carte grise comme un service additionnel sur son site, fixer ses propres honoraires, et offrir une experience client superieure a ce qui existe sur le marche.
