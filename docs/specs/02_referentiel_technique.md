# Référentiel Technique — Carte Grise B2B

Source : Doc 2 v1 — Base de données de référence complète
Périmètre : VN + VO | Motos + Voitures | Pro → Particulier

---

## 1. Référentiel documents (31 pièces)

### Formulaires

| Code | Document | Description & règles | Validité | VN/VO | Contrôles automatisés |
|------|----------|----------------------|----------|-------|----------------------|
| D-01 | Cerfa 13749*06 — Demande CG VN | Signé titulaire (+co-tit). Champs : identité, adresse, infos véhicule. | Daté signé | VN | Complétude champs, signature présente, Nom↔CNI (C-01), Adresse↔justif (C-04), Infos véhicule↔COC (C-06), Pas de rature (V-23) |
| D-02 | Cerfa 13750*07 — Demande CG VO | Idem D-01 + infos ancien titulaire + n° formule ancienne CG. | Daté signé | VO | Idem D-01 + N° formule↔CG barrée, Ancien titulaire↔CG |
| D-03 | Cerfa 15776*02 — Cession | Acte de vente. Signatures vendeur + acquéreur + co-tit. Tampon SIRET pro obligatoire. Original. | Date cession fait foi | VO | Signatures présentes (V-34), Tampon SIRET, VIN↔CG (C-06), Date cession↔CG barrée (C-12), Vendeur=pro, vendeur initial DA=titulaire CG (C-11) |
| D-04 | Cerfa 13757*03 — Mandat | Procuration au pro. OBLIGATOIRE pour toute démarche par un tiers. Identité mandant + mandataire + immat. | Daté signé | VN + VO | Complétude, Signature (V-34), Identité mandant↔CNI (C-01) |
| D-05 | Cerfa 13751*02 — DA pro | Déclaration d'Achat. Enregistrée SIV < 15 jours. Génère récépissé DA (D-21). | < 15j après achat | VO | VIN DA↔VIN CG (C-06), Vendeur DA↔titulaire CG (C-11), DA enregistrée dans les délais |
| D-06 | Cerfa 13753*04 — Perte CG | Si CG perdue. Signé par ancien titulaire. | Pas d'exp. | VO si perte | Identité déclarant↔titulaire SIV |

### Identité acheteur

| Code | Document | Description & règles | Validité | VN/VO | Contrôles automatisés |
|------|----------|----------------------|----------|-------|----------------------|
| D-07 | CNI | Recto/verso. Règle 2004-2013 : +5 ans pour majeurs. Nom jeune fille → livret famille (D-26). | 15 ans (maj) / 10 ans (min) + 5 ans si 2004-2013 | VN + VO | Validité (V-11, règle 2004-2013), OCR nom/prénom/date naissance, Nom↔Cerfa (C-01), Nom↔permis (C-03), Âge→mineur? (C-16), Lisibilité (V-20/V-21), KYC anti-fraude (V-37) |
| D-08 | Passeport | Alternative CNI. Si hors UE : titre séjour (D-09) requis en plus. | 10 ans (maj) / 5 ans (min) | VN + VO | Idem D-07, Pays émetteur → si hors UE : D-09 requis |
| D-09 | Titre de séjour | Carte séjour temp/pluri, carte résident, certif algérien, carte UE/EEE. Récépissé renouvellement accepté (risqué). | Variable / Récépissé : 3-6 mois | Si étranger | Validité (V-13), Nom↔Cerfa, Adresse↔justif (C-05), Récépissé→SEMI-AUTO |
| D-10 | Permis de conduire | Catégorie doit correspondre au véhicule. AM=cyclo, A1=125cc, A2=35kW, A=tout, B=voiture. Permis étranger : traduction + valide 1 an max après résidence FR. **OBLIGATOIRE pour le TITULAIRE PRINCIPAL uniquement** (loi 18/11/2016 + décret 2017-1278). **EXCEPTIONS :** PM=pas de permis (CNI gérant suffit), Co-titulaire=pas de permis requis, CEPC accepté (vérif NEPH). | En cours validité | VN + VO (sauf PM) | Validité (V-12), Catégorie↔véhicule (C-15), Nom↔CNI (C-03), Âge↔catégorie (C-16), Permis étranger→durée résidence, Si PM→permis non requis, Si co-tit sans permis→OK |

### Justificatif domicile

| Code | Document | Description & règles | Validité | VN/VO | Contrôles automatisés |
|------|----------|----------------------|----------|-------|----------------------|
| D-11 | Facture énergie / télécom | EDF, gaz, eau, tél, Internet. Nom + prénom titulaire CG. **REFUSÉS :** échéancier, lettre relance, déclaration pré-remplie, fiche paie, facture manuscrite. | < 6 mois | VN + VO | Date < 6 mois (V-14), Nom↔CNI/Cerfa, Adresse↔Cerfa (C-04), Rejet types interdits |
| D-12 | Avis d'imposition | IR, taxe foncière, taxe habitation. Année précédente acceptée. | Dernière année | VN + VO | Nom + adresse↔Cerfa (C-04) |
| D-13 | Attestation assurance habitation | Attestation (pas échéancier). Nom + adresse. | < 6 mois | VN + VO | C-04 |
| D-14 | Quittance de loyer | UNIQUEMENT si émise par agence RCS. Manuscrite entre particuliers = REFUSÉE. | < 6 mois + agence RCS | VN + VO | Vérif RCS, C-04 |
| D-15 | Pack hébergement (4 docs) | Si pas de justif au nom du titulaire : 1) Attestation honneur hébergeant (signée), 2) Justif domicile hébergeant < 6 mois, 3) CNI hébergeant valide, 4) Doc officiel hébergé (impôt, Sécu, CAF, paie) | Justif < 6 mois / CNI valide | VN + VO | 4 docs à croiser ensemble, Adresse attestation↔justif hébergeant, CNI hébergeant valide, SEMI-AUTO minimum |

### Documents véhicule

| Code | Document | Description & règles | Validité | VN/VO | Contrôles automatisés |
|------|----------|----------------------|----------|-------|----------------------|
| D-16 | COC | Certificat conformité européen constructeur. CNIT, VIN, marque, type, puissance, CO2 (WLTP + NEDC), norme Euro. Peut être en langue étrangère. | Pas d'exp. | VN | CNIT↔base UTAC (C-08), VIN↔Cerfa (C-06), Puissance↔base (C-09), CO2 WLTP→calcul malus (C-10), Langue étrangère→WARNING |
| D-17 | CG barrée | Barrée diag + "vendu le" + date + heure + signature vendeur. N° formule visible. Coupon rempli. Dans flux DA : CG au nom du vendeur initial (pas du pro). | Cession < 30 jours | VO | Barre diag détectée (V-33), Mention vendu le + date + heure (OCR), Signature (V-34), Nb signatures↔co-tit (C-13), N° formule↔Cerfa, VIN↔Cerfa/cession (C-06), Titulaire↔DA (C-11), Dates (C-12) |
| D-18 | Contrôle technique | Voitures > 4 ans obligatoire. Motos > 5 ans obligatoire (depuis 04/2024). Dispensés : < 4 ans (voit), < 5 ans (moto), collection < 1960. **CT volontaire sur dispensé → DEVIENT obligatoire.** Résultat : A (OK) / S (majeur) / R (critique). Contre-visite : < 2 mois. **Pour vente : < 6 mois à date SAISIE SIV (pas date commande).** | 2 ans (voit) / 3 ans (moto) — Pour vente : < 6 mois | VO sauf dispenses | Date < 6 mois à saisie SIV (V-16), 5-6 mois→WARNING (V-17), Résultat favorable (V-35), Immat CT↔CG (C-07), VIN CT↔VIN CG (C-06), Dispense par âge véhicule, CT volontaire=obligatoire |
| D-19 | Attestation assurance véhicule | **OBLIGATOIRE** (décret 2017-1278). Attestation, carte verte, ou Mémo Véhicule Assuré (depuis 2025). Doit identifier le véhicule par immat (VO) ou VIN (VN). **Pas forcément au nom du titulaire CG.** Attestation provisoire (1 mois) acceptée. | En cours validité au jour de la saisie SIV | VN + VO | Validité (V-19), Immat/VIN↔véhicule (C-06), Provisoire < 7j restants→WARNING, Absence=BLOCAGE (V-09) |
| D-20 | Code cession ANTS | 5 caractères. Généré par vendeur sur ANTS. Pro habilité SIV : peut s'en passer (accès direct). | 15 jours | VO | Format + délai (V-18), Si pro SIV direct : ignorer |
| D-21 | Récépissé DA | PDF généré après enregistrement DA (D-05). Obligatoire dans le dossier du client final. VIN, immat, SIREN pro, date. | Pas d'exp. | VO | Présence (V-36), VIN↔dossier (C-06), SIREN↔pro (C-11) |
| D-22 | CSA / HistoVec | Certificat situation administrative. Gage, OTCI, vol, VEC/VEI, historique. GRATUIT en ligne. Consulté en Phase 0. | < 15j pour vente / Consultation gratuite | VO (Phase 0) | Gage (C-17)→STOP, OTCI (C-18)→STOP, Vol (C-20)→STOP, VEC/VEI (C-19)→WARNING |

### Documents personne morale

| Code | Document | Description & règles | Validité | Applicable | Contrôles automatisés |
|------|----------|----------------------|----------|------------|----------------------|
| D-23 | Kbis / avis SIRENE | Raison sociale, siège, représentant, SIREN. Auto-entrepreneur : avis SIRENE (pas de Kbis). | < 3 mois | Si acheteur PM | Date (V-15), SIREN↔Cerfa, Représentant↔CNI |
| D-24 | CNI représentant légal | Gérant/président sur Kbis. Si absent Kbis : pouvoir/statuts (D-25) requis. | En cours validité | Si PM | Nom↔Kbis, Si différent→ESCALADE |
| D-25 | Statuts / PV AG | Si signataire absent Kbis. SCI, association. | Dernière version | Si PM + besoin | ESCALADE systématique |

### Documents spéciaux

| Code | Document | Description & règles | Validité | Applicable | Contrôles automatisés |
|------|----------|----------------------|----------|------------|----------------------|
| D-26 | Livret de famille | Si nom marital vs jeune fille sur CNI. Si acheteur mineur (lien parent). Si co-titulaires mariés. | Pas d'exp. À jour. | Si applicable | Noms livret↔CNI/Cerfa |
| D-27 | Autorisation parentale | Si acheteur mineur. Signée parent(s)/tuteur. | Pas d'exp. | Si mineur | Signature parent, Livret↔lien, Âge (C-16) |
| D-28 | Ordonnance tutelle/curatelle | Si acheteur sous protection juridique. | En cours validité | Si applicable | ESCALADE systématique |
| D-29 | Acte décès + certif hérédité | Si CG au nom décédé. Accord héritiers si indivision. | Pas d'exp. | VO si décès | ESCALADE systématique |
| D-30 | Mainlevée de gage | Document organisme créancier. | Pas d'exp. | VO si gage | ESCALADE systématique |
| D-31 | Attestation vérif identité pro | Attestation que le pro a vérifié physiquement l'identité du client. Case + signature électronique dans le portail. Archivée 5 ans. | Datée signée | VN + VO OBLIGATOIRE | Présence (V-38), Niveau 1 authentification |

---

## 2. Règles de cohérence croisée (21 règles C-XX)

Exécutées automatiquement en Phase 1. C-17 à C-20 détectables aussi en Phase 0 via HistoVec.

### Identité ↔ Formulaires

| Code | Vérification | Règle | Documents | Si échec |
|------|-------------|-------|-----------|---------|
| C-01 | Nom CNI ↔ Cerfa | Fuzzy match : > 95% = OK, 85-95% = WARNING, < 85% = BLOCAGE. Tolérance : accents, tirets, apostrophes. Nom de jeune fille → D-26 requis. Prénoms composés : ordre peut varier. | D-07 + D-01/D-02 | < 85% → BLOCAGE + ESCALADE / 85-95% → WARNING + vérif |
| C-02 | Nom CNI ↔ Cerfa cession | Idem C-01, volet acquéreur du Cerfa cession. | D-07 + D-03 | Idem C-01 |
| C-03 | Nom CNI ↔ permis | Changement de nom non reporté sur le permis. | D-07 + D-10 | WARNING si mineure / BLOCAGE si totale |
| C-04 | Adresse Cerfa ↔ justif domicile | Normalisation : av./avenue, r./rue, bd/boulevard. Hébergement : adresse = celle de l'hébergeant. | D-01/02 + D-11 à D-15 | Diff mineure (abréviation) → OK / Diff majeure → BLOCAGE |
| C-05 | Adresse Cerfa ↔ titre séjour | Si étranger. Si titre à ancienne adresse → justif complémentaire. | D-01/02 + D-09 + D-11 à D-15 | BLOCAGE si divergence totale |

### Véhicule ↔ Documents

| Code | Vérification | Règle | Documents | Si échec |
|------|-------------|-------|-----------|---------|
| C-06 | VIN identique sur TOUS les docs | 17 caractères. Caractères interdits : I, O, Q. Confusions fréquentes : O/0, I/1, B/8, S/5. Doit être identique sur : Cerfa, CG, COC, CT, assurance, cession, DA, récépissé DA. | Tous docs véhicule | 1 caractère diff → BLOCAGE TOTAL / Format invalide → BLOCAGE |
| C-07 | Immatriculation cohérente | Même immat sur CG, Cerfa, CT, cession, DA. | D-17 + D-01/02 + D-18 + D-03 + D-05 | Diff → BLOCAGE |
| C-08 | CNIT COC ↔ base UTAC | Le CNIT du COC doit exister en base nationale. | D-16 ↔ base UTAC | Absent + VN récent → WARNING (délai) / Absent + VO → BLOCAGE |
| C-09 | Puissance COC ↔ base | Impact taxe régionale + malus. | D-16 ↔ base UTAC | Écart > 1 CV → WARNING / > 3 CV → BLOCAGE |
| C-10 | CO2 WLTP vs NEDC | Malus calculé sur WLTP. Si COC montre 2 valeurs → utiliser WLTP. | D-16 | Mauvaise valeur = malus incorrect |

### Cession + DA ↔ Cohérence

| Code | Vérification | Règle | Documents | Si échec |
|------|-------------|-------|-----------|---------|
| C-11 | Chaîne de propriété | Vendeur initial (titulaire CG) → DA pro → Cerfa cession pro → client final. Vendeur sur DA = titulaire CG. Vendeur sur Cerfa cession = pro. | D-05 + D-21 + D-17 + D-03 | Incohérence → ESCALADE / DA absente → BLOCAGE (V-36) |
| C-12 | Dates CG barrée ↔ DA ↔ cession | CG barrée = date vente au pro. DA enregistrée < 15j après. Cerfa cession client = date vente client final. | D-17 + D-05 + D-03 | Heure absente sur CG → BLOCAGE / DA > 15j après CG → WARNING |
| C-13 | Nb signatures ↔ co-titulaires | Si co-tit sur CG → tous doivent signer CG barrée + cession. | D-17 + D-03 | Signature manquante → BLOCAGE |
| C-14 | Date CT ↔ date saisie SIV | CT < 6 mois à la saisie SIV (pas à la commande). Contre-visite < 2 mois. | D-18 + date saisie | > 6 mois → BLOCAGE / 5-6 mois → WARNING |
| C-15 | Catégorie permis ↔ véhicule | AM=cyclo 50cc, A1=125cc/11kW, A2=35kW, A=tout, B=voiture. S'applique UNIQUEMENT au titulaire principal (C.1). Co-titulaire sans permis → pas de vérif. Personne morale → pas de vérif. | D-10 + D-16/D-17 | Incohérence → BLOCAGE |
| C-16 | Âge ↔ catégorie véhicule | < 14 : rien. 14-15 : AM. 16-17 : AM+A1. ≥ 18 : A2+B. ≥ 20 (+2 ans A2) : A. | D-07 + véhicule | Incohérence → BLOCAGE + ESCALADE |

### Statut SIV (Phase 0 + Phase 2)

| Code | Vérification | Règle | Documents | Si échec |
|------|-------------|-------|-----------|---------|
| C-17 | Gage actif | Impossible de transférer. DA impossible si gage. Détectable via HistoVec Phase 0. | SIV / D-22 + D-30 | BLOCAGE CRITIQUE |
| C-18 | OTCI (opposition) | Aucune opération possible. Détectable Phase 0. | SIV / D-22 | BLOCAGE CRITIQUE + notif pro |
| C-19 | VEC/VEI | VEC : CT post-réparation requis. VEI : procédure spécifique. Détectable Phase 0. | SIV / D-22 + D-18 | BLOCAGE |
| C-20 | Vol signalé | STOP immédiat. | SIV / D-22 | BLOCAGE CRITIQUE + alerte |
| C-21 | Doublon VIN interne | Même VIN déjà en cours de traitement. | Base interne | BLOCAGE + notif pro |

---

## 3. Critères de verrouillage (38 règles V-XX)

Phase 0 = gratuit, Phase 1 = pré-qualif, Phase 2 = traitement.

### Documents manquants

| Code | Critère | Contrôle | Phase | Action si KO | Sévérité |
|------|---------|----------|-------|-------------|---------|
| V-01 | CNI absente | Présence fichier | Phase 1 | BLOCAGE + relance | Bloquant |
| V-02 | Permis absent | Présence fichier | Phase 1 | BLOCAGE + relance | Bloquant |
| V-03 | Justif domicile absent | Présence fichier | Phase 1 | BLOCAGE + relance | Bloquant |
| V-04 | Cerfa CG absent | Présence fichier | Phase 1 | BLOCAGE + relance | Bloquant |
| V-05 | Mandat absent | Présence fichier | Phase 1 | BLOCAGE + relance | Bloquant |
| V-06 | Cerfa cession absent (VO) | Présence fichier | Phase 1 | BLOCAGE + relance pro | Bloquant |
| V-07 | CG barrée absente (VO) | Présence sauf perte | Phase 1 | BLOCAGE + relance pro | Bloquant |
| V-08 | CT absent (VO) | Présence + vérif dispense | Phase 1 | BLOCAGE + relance | Bloquant |
| V-09 | Assurance absente | Présence fichier | Phase 1 | BLOCAGE + relance spécifique assurance | Bloquant |
| V-10 | COC absent (VN) | Présence fichier | Phase 1 | BLOCAGE + relance pro | Bloquant |

### Validité

| Code | Critère | Contrôle | Phase | Action si KO | Sévérité |
|------|---------|----------|-------|-------------|---------|
| V-11 | CNI expirée | Date exp (règle +5 ans 2004-2013) | Phase 1 | BLOCAGE + relance | Bloquant |
| V-12 | Permis expiré | Date validité | Phase 1 | BLOCAGE + relance | Bloquant |
| V-13 | Titre séjour expiré | Date exp | Phase 1 | BLOCAGE (récépissé → SEMI-AUTO) | Bloquant |
| V-14 | Justif domicile > 6 mois | Date document | Phase 1 | BLOCAGE + relance | Bloquant |
| V-15 | Kbis > 3 mois | Date Kbis | Phase 1 | BLOCAGE + relance | Bloquant |
| V-16 | CT > 6 mois à saisie SIV | Calcul date | Phase 1 | BLOCAGE "nouveau CT requis" | Bloquant |
| V-17 | CT entre 5-6 mois | Calcul prédictif | Phase 1 | WARNING "expire bientôt" | Warning |
| V-18 | Code cession > 15 jours | Calcul date | Phase 1 | WARNING (sauf pro SIV direct) | Bloquant si non pro |
| V-19 | Assurance expirée | Date validité attestation/Mémo | Phase 1 | BLOCAGE + relance | Bloquant |

### Qualité / Lisibilité

| Code | Critère | Contrôle | Phase | Action si KO | Sévérité |
|------|---------|----------|-------|-------------|---------|
| V-20 | Document illisible | Score OCR < seuil | Phase 1 | BLOCAGE + relance "re-scanner" | Bloquant |
| V-21 | Scan tronqué | Détection bords | Phase 1 | BLOCAGE + relance | Bloquant |
| V-22 | Langue étrangère | Détection langue OCR | Phase 1 | BLOCAGE + traduction assermentée | Bloquant |
| V-23 | Rature sur Cerfa | Détection visuelle | Phase 1 | BLOCAGE + nouveau Cerfa | Bloquant |

### Cohérence

| Code | Critère | Contrôle | Phase | Action si KO | Sévérité |
|------|---------|----------|-------|-------------|---------|
| V-24 | VIN incohérent | C-06, C-07 | Phase 1 | BLOCAGE TOTAL | Bloquant critique |
| V-25 | Identité incohérente | C-01 à C-05 | Phase 1 | BLOCAGE ou ESCALADE | Bloquant |
| V-26 | Chaîne propriété brisée | C-11 | Phase 1 | ESCALADE | Bloquant critique |
| V-27 | Permis ≠ véhicule | C-15 | Phase 1 | BLOCAGE | Bloquant |
| V-28 | Âge incompatible | C-16 | Phase 1 | ESCALADE | Bloquant |

### Statut SIV

| Code | Critère | Contrôle | Phase | Action si KO | Sévérité |
|------|---------|----------|-------|-------------|---------|
| V-29 | Gage actif | C-17 (Phase 0 + Phase 2 SIV) | Phase 0+2 | BLOCAGE CRITIQUE + notif pro | Bloquant critique |
| V-30 | OTCI active | C-18 | Phase 0+2 | BLOCAGE CRITIQUE + STOP | Bloquant critique |
| V-31 | VEC/VEI actif | C-19 | Phase 0+2 | BLOCAGE + ESCALADE | Bloquant critique |
| V-32 | Vol signalé | C-20 | Phase 0+2 | BLOCAGE CRITIQUE + alerte | Bloquant critique |
| V-33 | CG non barrée | Analyse image diagonale | Phase 1 | BLOCAGE + relance pro | Bloquant |
| V-34 | Signature manquante | Détection zone signature | Phase 1 | BLOCAGE + relance | Bloquant |
| V-35 | CT défavorable critique | Lecture résultat CT | Phase 1 | BLOCAGE TOTAL | Bloquant critique |
| V-36 | DA / récépissé DA absent | Présence si flux VO rachat | Phase 1 | BLOCAGE + relance pro | Bloquant |
| V-37 | KYC anti-fraude échec | Service KYC systématique | Phase 2 | Suspect→ESCALADE / Rejeté→BLOCAGE | Bloquant |
| V-38 | Attestation identité pro absente | Présence D-31 | Phase 1 | BLOCAGE "pro doit attester" | Bloquant |

---

## 4. Cas d'usage (20 scénarios S-XX)

### Cas acheteur

| Code | Scénario | Type | Spécificités | Pièges fréquents | Niveau |
|------|----------|------|-------------|-----------------|--------|
| S-01 | Acheteur société (PM) | VN+VO | Docs suppl : D-23 (Kbis < 3 mois), D-24 (CNI représentant), D-25 (statuts si besoin). SIREN Kbis↔Cerfa. **PERMIS NON REQUIS pour PM.** Auto-entrepreneur = personne physique → permis requis. | Kbis périmé. Gérant changé Kbis pas MAJ. SCI/association = docs spécifiques. Signataire sans pouvoir. | Semi-Auto |
| S-02 | Co-titulaires mariés/pacsés | VN+VO | 2 noms sur Cerfa. CNI × 2. Mandat × 2. Livret famille ou attestation PACS. **PERMIS : seul le titulaire principal (C.1).** Co-titulaire → CNI uniquement. | Nom jeune fille→D-26 requis. Adresses différentes. CNI expirée d'un des 2. Confusion : demander permis au co-titulaire. | Semi-Auto |
| S-03 | Co-titulaires non mariés | VN+VO | 2 justifs domicile. Titulaire principal à déterminer. **PERMIS : seul le titulaire principal.** | Confusion titulaire principal. 2 départements → quelle taxe ? Co-titulaire mineur interdit. | Semi-Auto |
| S-04 | Acheteur mineur | VN+VO | D-27 (autorisation parentale), D-26 (livret famille). CNI mineur + CNI parent. Permis AM ou A1. | Véhicule > 50cc interdit mineur. Parents divorcés : qui signe ? Permis AM/A1 manquant. | Escalade Humaine |
| S-05 | Acheteur étranger résident | VN+VO | Titre de séjour (D-09) ou passeport + titre. Permis étranger : traduction si non FR, valide 1 an après résidence. | Titre expiré. Récépissé seul (risqué). Nom différent (transcription). Permis non traduit. | Semi-Auto |
| S-06 | Acheteur hébergé | VN+VO | Pack hébergement D-15 (4 docs). | Attestation non signée. CNI hébergeant expirée. Justif hébergeant > 6 mois. Quittance manuscrite = refusée. | Semi-Auto |
| S-07 | Acheteur tutelle/curatelle | VN+VO | Ordonnance juge (D-28). CNI tuteur/curateur. Autorisation juge si achat > seuil. | Curatelle simple vs renforcée = pouvoirs différents. | Escalade Humaine |

### Cas véhicule (VO)

| Code | Scénario | Type | Spécificités | Pièges fréquents | Niveau |
|------|----------|------|-------------|-----------------|--------|
| S-08 | CG adresse non MAJ | VO | Coupon changement adresse. | Plus de coupon = CG aurait dû être refaite. Rejet si > 3 changements non déclarés. | Semi-Auto |
| S-09 | CG perdue | VO | Déclaration perte (D-06). Duplicata ou procédure pro. | Ancien proprio absent/injoignable. Véhicule gagé : duplicata impossible. | Escalade Humaine |
| S-10 | CG titulaire décédé | VO | Acte décès + certif hérédité (D-29). Accord héritiers si indivision. | Succession non réglée. Héritiers en désaccord. | Escalade Humaine |
| S-11 | Véhicule gagé | VO | Mainlevée (D-30) requise. Détectable Phase 0 via HistoVec. | DA impossible si gage actif. Fausse mainlevée. | Escalade Humaine |
| S-12 | Véhicule OTCI | VO | Opposition au transfert. Détectable Phase 0. | PV impayés ancien proprio. Vol signalé. | Escalade Humaine |
| S-13 | Véhicule VEC/VEI | VO | VEC : 2ème CT favorable après réparation. VEI : procédure remise en circulation. | VEI revendu sans procédure = illégal. VEC sans CT = rejet. | Escalade Humaine |
| S-14 | Véhicule ancien FNI | VO | Conversion FNI → SIV automatique. | Données FNI incomplètes. DA difficile sur FNI. | Semi-Auto |
| S-15 | Erreur sur ancienne CG | VO | Preuve erreur + correction préalable. | Erreur VIN = blocage total SIV. Correction obligatoire avant cession. | Escalade Humaine |
| S-16 | Double cession | VO | Véhicule revendu sans CG intermédiaire. Chaîne DA à reconstituer. | Chaîne brisée = rejet SIV. DA manquante. | Escalade Humaine |

### Cas VN spéciaux

| Code | Scénario | Type | Spécificités | Pièges fréquents | Niveau |
|------|----------|------|-------------|-----------------|--------|
| S-17 | VN importé UE | VN | Quitus fiscal. Certif conformité DREAL si COC non reconnu. | COC non reconnu → RTI. TVA marge vs intracommunautaire. Neuf fiscal < 6 mois. | Escalade Humaine |
| S-18 | VN importé hors UE | VN | 846A dédouanement. PV RTI. | 846A manquant. RTI refusée. UK post-Brexit. | Escalade Humaine |
| S-19 | VN moto transformée | VN | PV RTI si changement catégorie. | Catégorie modifiée sans RTI = rejet. | Escalade Humaine |
| S-20 | VN démo/direction | VN/VO | Immat pro puis cession. Double opération. | TVA neuf fiscal vs occasion. Malus déjà payé. Statut fiscal. | Semi-Auto |
