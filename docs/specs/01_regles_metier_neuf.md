# Règles Métier — Véhicule Neuf (Pro → Particulier)

## Identifiant de cas : `NEUF_PRO_PARTICULIER`

---

## 1. Documents obligatoires

| Document | Obligatoire | Criticité absence |
|----------|-------------|-------------------|
| Certificat de Conformité (COC) | Oui | BLOQUANT |
| Facture d'achat | Oui | BLOQUANT |
| Pièce d'identité acheteur | Oui | BLOQUANT |
| Justificatif de domicile | Oui | BLOQUANT |
| Permis de conduire | Oui | BLOQUANT |
| Attestation d'assurance | Oui | BLOQUANT |
| Kbis vendeur | Non | WARNING si SIRET douteux |

---

## 2. Règles spécifiques au cas neuf

- Pas de carte grise existante (véhicule jamais immatriculé)
- Pas de CERFA 15776 requis
- Pas de déclaration de cession
- Le COC fait foi pour l'homologation (remplace la réception nationale)
- Le VIN ne doit pas figurer dans le SIV (vérification obligatoire)

---

## 3. Règles par document

### COC (Certificat de Conformité)

| Champ | Extraction | Validation | Criticité |
|-------|-----------|------------|-----------|
| VIN | Alphanum 17 chars | Algo ISO 3779 + WMI check | BLOQUANT |
| CNIT | Format `AA-000-AA-00-A-000` | Présence + format | BLOQUANT |
| Marque | Texte libre | Non vide | BLOQUANT |
| Énergie | Code normalisé | Table de mapping | BLOQUANT |
| Puissance nette (kW) | Décimal | > 0 | BLOQUANT |
| Carrosserie | Code EU | Table codes EU | BLOQUANT |
| Places assises | Entier | 1–9 | BLOQUANT |
| PTAC (kg) | Entier | > 0 | BLOQUANT |
| N° homologation EU | Format `e[pays]*[ref]*` | Format + non vide | BLOQUANT |
| Puissance fiscale (CV) | Entier | Calculée si absente | WARNING |
| Constructeur | Texte libre | Non vide | WARNING |
| Date 1ère immat. UE | Date ou vide | Vide pour neuf pur | INFO |

**Règles de fraude COC :**
- WMI (3 premiers chars VIN) doit correspondre au constructeur déclaré dans le COC
- Si COC en langue étrangère : traduction officielle requise (hors langues UE reconnues)
- COC photocopié ou manuscrit : REJET

### Facture d'achat

| Champ | Extraction | Validation | Criticité |
|-------|-----------|------------|-----------|
| VIN | Alphanum 17 chars | = VIN COC | BLOQUANT |
| Marque | Texte libre | = Marque COC (normalisé) | BLOQUANT |
| Énergie | Texte libre | Cohérent avec COC | BLOQUANT |
| Date de vente | Date | ≤ date demande | BLOQUANT |
| SIRET vendeur | 14 chiffres | Luhn + API INSEE actif | BLOQUANT |
| Nom vendeur | Texte libre | Non vide | BLOQUANT |
| Nom acheteur | Texte libre | = Nom CNI (normalisé) | BLOQUANT |
| Mention "véhicule neuf" | Texte | Présent dans doc | BLOQUANT |
| Prix TTC | Décimal | > 0 | WARNING |
| Kilométrage | Entier | ≤ 100 km pour neuf | WARNING |
| N° facture | Alphanum | Non vide | INFO |

**Erreurs fréquentes :**
- Facture pro-forma : REJET (demander facture définitive)
- Correction manuscrite sur facture : REJET
- SIRET avec espaces : normalisation automatique

### Pièce d'identité

| Champ | Extraction | Validation | Criticité |
|-------|-----------|------------|-----------|
| Nom de naissance | Majuscules | Non vide | BLOQUANT |
| Prénom(s) | Texte | Non vide | BLOQUANT |
| Date de naissance | Date | Age ≥ 18 ans | BLOQUANT |
| Date d'expiration | Date | ≥ date demande | BLOQUANT |
| N° document | Alphanum | Non vide | BLOQUANT |
| MRZ ligne 1 & 2 | Format ICAO 9303 | Cohérence champs visuels | BLOQUANT si présent |

**Documents acceptés :**
- CNI française (recto/verso obligatoire)
- Passeport (français ou étranger valide)
- Titre de séjour valide avec droit de résidence

**Règle expiration CNI :**
- CNI périmée depuis ≤ 5 ans : acceptée uniquement pour ressortissants français (règle transitoire 2014–2021, vérifier version du document)
- CNI périmée > 5 ans : REJET

### Justificatif de domicile

| Champ | Extraction | Validation | Criticité |
|-------|-----------|------------|-----------|
| Nom titulaire | Texte | = Nom CNI (normalisé, tolérance nom d'usage) | BLOQUANT |
| Adresse complète | Texte | Non vide + validation BAN | BLOQUANT |
| Code postal | 5 chiffres | Format + cohérence ville | BLOQUANT |
| Date document | Date | Délai selon type (voir table) | BLOQUANT |

**Délais de validité par type :**

| Type de justificatif | Délai max |
|---------------------|-----------|
| Facture EDF / Engie / eau | 3 mois |
| Facture téléphone fixe ou mobile | 3 mois |
| Quittance de loyer | 3 mois |
| Relevé bancaire | 3 mois |
| Avis d'imposition | 1 an (année en cours) |
| Attestation hébergeur | Aucun délai (mais pièces hébergeur requises) |

**Attestation d'hébergement :**
- Formulaire spécifique signé par l'hébergeur
- + CNI hébergeur (valide)
- + Justificatif de domicile de l'hébergeur (< 3 mois)

### Permis de conduire

| Champ | Extraction | Validation | Criticité |
|-------|-----------|------------|-----------|
| Nom | Texte | = Nom CNI | BLOQUANT |
| Prénom | Texte | = Prénom CNI | BLOQUANT |
| Date de naissance | Date | = Date naissance CNI | BLOQUANT |
| N° permis | Alphanum | Non vide | BLOQUANT |
| Catégories valides | Codes | Catégorie adaptée au véhicule | BLOQUANT |
| Date validité | Date | ≥ date demande | BLOQUANT |
| Codes restrictions | Codes 01–99 | Vérifier compatibilité | WARNING |

**Catégories requises par type véhicule :**

| Type véhicule | Catégorie minimale |
|--------------|-------------------|
| VP ≤ 3,5T (voiture) | B |
| Cyclo 50cc | AM ou B |
| Moto ≤ 125cc | A1 ou B (+ formation) |
| Moto 125cc–35kW | A2 |
| Moto > 35kW | A |
| VUL ≤ 3,5T | B |
| VUL > 3,5T ≤ 7,5T | C1 |
| VUL > 7,5T | C |
| Camping-car > 3,5T | C ou BE selon PTAC |

### Attestation d'assurance

| Champ | Extraction | Validation | Criticité |
|-------|-----------|------------|-----------|
| Nom assuré | Texte | = Nom CNI (tolérance nom d'usage) | BLOQUANT |
| Prénom assuré | Texte | = Prénom CNI | BLOQUANT |
| VIN | Alphanum 17 chars ou absent | = VIN COC si présent | BLOQUANT |
| Marque / Modèle | Texte | Cohérent avec COC | WARNING |
| Date d'effet | Date | ≤ date demande | BLOQUANT |
| Date d'échéance | Date | ≥ date demande | BLOQUANT |
| Garanties | Texte | RC minimum (art. L211-1) | BLOQUANT |

**Règle assurance provisoire :**
- VIN absent acceptable si : marque + modèle cohérents avec COC ET date d'effet ≤ date demande
- VIN partiel (< 17 chars) : REJET, nouvelle attestation requise

---

## 4. Croisements inter-documents

### VIN

| Source A | Source B | Règle | Criticité |
|----------|----------|-------|-----------|
| VIN COC | VIN Facture | Égalité stricte 17 chars | BLOQUANT |
| VIN COC | VIN Assurance | Égalité stricte si présent | BLOQUANT |
| VIN COC | SIV | Absent du SIV (jamais immatriculé) | BLOQUANT |
| WMI (VIN[0:3]) | Constructeur COC | Correspondance base WMI | ALERTE FRAUDE |

### Identité

| Source A | Source B | Règle | Tolérance | Criticité |
|----------|----------|-------|-----------|-----------|
| Nom CNI | Nom Facture | Correspondance normalisée | Accents, casse | BLOQUANT |
| Nom CNI | Nom Permis | Correspondance normalisée | Accents, casse | BLOQUANT |
| Nom CNI | Nom Assurance | Correspondance ou nom d'usage | Voir règle | WARNING |
| Prénom CNI | Prénom Facture | 1er prénom obligatoire | Composés | BLOQUANT |
| DDN CNI | DDN Permis | Égalité stricte | Aucune | BLOQUANT |
| Nom CNI | Nom Domicile | Correspondance ou attestation | Nom d'usage | BLOQUANT |

**Seuils de matching flou :**
```
ratio ≥ 97%  → MATCH auto (différence OCR probable)
ratio 85–96% → WARNING + flag vérification recommandée
ratio 70–84% → CORRECTION demandée
ratio < 70%  → REJET ou agent obligatoire
```

### Véhicule

| Champ | COC | Facture | Règle | Criticité |
|-------|-----|---------|-------|-----------|
| Marque | Valeur de référence | Doit correspondre | Normalisation + alias | BLOQUANT |
| Énergie | Valeur de référence | Doit correspondre | Table de mapping | BLOQUANT |
| Puissance kW | Valeur de référence | Cohérence si présent | ±5% | WARNING |
| Carrosserie | Valeur de référence | Cohérence | Table de mapping | WARNING |

### Temporel

| Vérification | Règle | Criticité |
|-------------|-------|-----------|
| Date facture | ≤ date demande | BLOQUANT |
| Date effet assurance | ≤ date demande | BLOQUANT |
| Date échéance assurance | ≥ date demande | BLOQUANT |
| Domicile | ≤ délai max selon type | BLOQUANT |
| Age acheteur | ≥ 18 ans (DDN + date demande) | BLOQUANT |

---

## 5. Moteur de décision

### Statuts de sortie

| Statut | Condition |
|--------|-----------|
| `ACCEPTE` | Score ≥ 95, 0 règle bloquante, tous docs présents |
| `CORRECTION` | Score 60–94 ou ≤ 2 warnings non bloquants |
| `REJET` | Règle bloquante déclenchée ou score < 60 |
| `FRAUDE` | Indicateur fraude détecté (VIN falsifié, doc altéré...) |
| `REVUE_AGENT` | Score 60–94 ou indicateur ambigu non bloquant |

### Règles bloquantes (court-circuit immédiat)

1. `vin_coc_facture_mismatch` — VIN différent entre COC et facture
2. `vin_already_registered` — VIN présent dans SIV
3. `identity_document_expired` — CNI/Passeport expiré
4. `insurance_expired` — assurance expirée à la date de demande
5. `siret_invalid_or_inactive` — SIRET incorrect ou société radiée
6. `fraud_indicator` — anomalie détectée (MRZ incohérente, doc altéré...)
7. `missing_mandatory_document` — document obligatoire absent
8. `driving_license_category_mismatch` — catégorie permis insuffisante
9. `buyer_underage` — acheteur mineur (< 18 ans)

### Pondération du score

| Critère | Poids |
|---------|-------|
| Cohérence VIN (COC/Facture/Assurance) | 30 |
| Cohérence identité (Nom/Prénom/DDN) | 20 |
| Validité des documents (dates) | 20 |
| Cohérence véhicule (marque, énergie...) | 15 |
| Validité adresse et domicile | 10 |
| Permis adapté au véhicule | 5 |

---

## 6. Variations

### Voiture vs Moto

- Catégorie permis différente (voir table § 3)
- Code carrosserie COC différent (L1e–L7e pour 2 roues, AF/AN pour VP)
- Puissance fiscale non applicable aux motos

### Véhicule importé hors UE

- COC EU valable si constructeur agréé CE
- Véhicule UK post-Brexit : procédure réception isolée DRIRE obligatoire
- Import USA/Japon : RTI (Réception à Titre Isolé) + quitus fiscal
- COC en langue étrangère : traduction officielle française obligatoire

### Co-titulaires

- Deux CNI + deux permis
- Assurance au nom des deux co-titulaires
- Facture mentionnant les deux noms

---

## 7. Cas limites connus

| Situation | Traitement |
|-----------|-----------|
| VIN avec O/0 ou I/1 confus (OCR) | Correction automatique + WARNING |
| Nom d'usage ≠ nom de naissance | WARNING + vérification agent si doute |
| Assurance provisoire sans VIN | Acceptable si marque/modèle cohérents |
| Kilométrage ≤ 100 km sur "neuf" | WARNING (véhicule de démonstration possible) |
| Kilométrage > 100 km sur "neuf" | CORRECTION — reclassifier ou justifier |
| Facture pro-forma | REJET — facture définitive requise |
| Correction manuscrite sur doc | REJET — document vierge requis |
| COC sans CNIT (import ancien) | Agent obligatoire + contact DRIRE |
| Permis étranger UE | Accepté directement |
| Permis étranger hors UE | Vérification échange ou validation CERT |
