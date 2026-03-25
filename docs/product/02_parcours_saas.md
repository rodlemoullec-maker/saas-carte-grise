# Parcours SaaS — Doc 1B

Cible : Pro DÉJÀ habilité SIV → On prépare le dossier, le pro soumet lui-même
Taxes : le pro gère dans son SIV | Honoraires : pré-auth CB ou SEPA | Pas d'opérateur

---

## Différence clé vs Full Service

| | Full Service | SaaS |
|--|-------------|------|
| Pro | Non habilité SIV | Déjà habilité SIV |
| Phase 1 | **Identique** | **Identique** |
| Phase 2 | Opérateur + extension navigateur | Livraison dossier prêt, pro soumet |
| Taxes | CB pro via notre portail | Pro gère dans son SIV |
| Honoraires | 30-60€/dossier | 10-25€/dossier |
| Coût plateforme | 2-5€/dossier | 0.70-2.50€/dossier |
| Marge | 25-58€ | 7.50-24.30€ (**TRÈS HAUTE**) |

---

## 1. Parcours VN SaaS (17 étapes)

Phase 1 identique Full Service. Différence en Phase 2 : dossier livré prêt, le pro soumet.

| N° | Étape | Qui | Ce qui se passe | Si problème |
|----|-------|-----|----------------|------------|
| **PARCOURS PRO (identique Full Service)** |||||
| 1-5 | Vente → Création dossier portail | Pro | Identique Full Service. | |
| **PHASE 1 — PRÉ-QUALIFICATION (identique Full Service)** |||||
| 6-10 | Complétude → DIAGNOSTIC + estimation taxes | Système | Identique Full Service. | |
| **🚦 GO / NO-GO** |||||
| 11 | Le pro lance le traitement | Pro | Le pro voit VERT. Clique "Lancer le traitement". Pré-auth CB honoraires (ou SEPA mensuel). **DIFFÉRENCE SAAS : le pro reçoit un DOSSIER PRÊT À SOUMETTRE. Pas d'opérateur de notre côté.** | |
| **PHASE 2 — KYC + LIVRAISON DOSSIER** |||||
| 12 | KYC anti-fraude (systématique) | Système | Identique Full Service. NIV.2. Si SUSPECT → alerte au pro "vérifier original". Si REJETÉ → BLOCAGE. | SUSPECT → étape 13. REJETÉ → BLOCAGE. |
| 13 | Livraison dossier prêt | Système | Le pro reçoit dans son portail : récapitulatif complet des données à saisir dans le SIV, toutes les données extraites et vérifiées, résultat KYC, estimation taxes, checklist validation finale. Le pro copie-colle ou vérifie dans son propre SIV. | |
| **LE PRO SOUMET LUI-MÊME** |||||
| 14 | Contrôle visuel CNI (NIV.3) | Pro | Le pro fait le contrôle visuel final. Il a déjà vu le client (NIV.1). | Doute → contacte notre support. |
| 15 | Soumission SIV | Pro | Le pro soumet dans SON accès SIV. Utilise le récapitulatif fourni. **TAXES : le pro paie avec sa CB ou prélèvement (s'il est agréé TP). C'est SON affaire, pas la nôtre.** | Rejet → le pro signale dans le portail. |
| 16 | CPI | Pro | CPI généré dans le SIV du pro. Remis au client. Archivable dans notre portail. **HONORAIRES : débit de la pré-auth CB.** | |
| 17 | CG + archivage | Système | CG envoyée au client. Archivage 5 ans. | |

---

## 2. Parcours VO SaaS (18 étapes)

Phase 0 + Phase 1 identiques. Le pro interroge SIV et soumet lui-même.

| N° | Étape | Qui | Ce qui se passe | Si problème |
|----|-------|-----|----------------|------------|
| 1-5 | Vente → Création dossier | Pro | Identique Full Service. DA enregistrée. | |
| **PHASE 0 — HISTOVEC (identique Full Service)** |||||
| 6 | Consultation HistoVec | Système | Identique Full Service. | |
| **PHASE 1 — PRÉ-QUALIFICATION (identique Full Service)** |||||
| 7-11 | Complétude → DIAGNOSTIC | Système | Identique Full Service. | |
| **🚦 GO / NO-GO** |||||
| 12 | Le pro lance le traitement | Pro | Idem VN SaaS. Pré-auth CB. Reçoit DOSSIER PRÊT. | |
| **PHASE 2 — KYC + LIVRAISON DOSSIER** |||||
| 13 | KYC anti-fraude | Système | Identique Full Service. | |
| 14 | Livraison dossier prêt | Système | Idem VN SaaS + résultat Phase 0 HistoVec inclus. | |
| **LE PRO SOUMET LUI-MÊME** |||||
| 15 | Contrôle visuel CNI (NIV.3) | Pro | Idem. | |
| 16 | Interrogation SIV + soumission | Pro | Le pro interroge le SIV (confirme statut VO). Puis soumet le changement de titulaire. Taxes : sa CB ou prélèvement. | Anomalie → signale dans portail. |
| 17 | CPI | Pro | CPI généré. Remis au client. Débit honoraires. | |
| 18 | CG + archivage | Système | CG envoyée. Archivage 5 ans. | |

---

## 3. Livrable "Dossier prêt" — Contenu exact

Le document livré au pro dans son portail doit contenir :

```
RÉCAPITULATIF DOSSIER — VIN: XXXXXXXXXXXXXXXXX
Statut : VERT ✓ — Prêt à soumettre

IDENTITÉ TITULAIRE
  Nom de naissance : MARTIN
  Prénoms : Jean Pierre
  Date de naissance : 15/03/1985
  Lieu de naissance : Paris (75)
  Adresse : 12 rue de la Paix, 75001 Paris

VÉHICULE
  VIN : [17 chars]
  CNIT : [format]
  Marque / Modèle : Renault Clio
  Énergie : Essence
  Puissance nette kW : 66
  CO2 WLTP : 112 g/km
  Puissance fiscale : 5 CV
  Places : 5

KYC RÉSULTAT : AUTHENTIQUE ✓

ESTIMATION TAXES (indicatif)
  Taxe régionale : 245€ (Île-de-France, 5 CV)
  Malus CO2 : 0€ (112g < 123g)
  Gestion : 11€
  Acheminement : 2.76€
  TOTAL ESTIMÉ : ~258.76€
  ⚠ Montant exact confirmé par le SIV au moment de la saisie

CHECKLIST VALIDATION FINALE
  ☐ VIN vérifié sur le véhicule physique
  ☐ Identité contrôlée en présentiel (NIV.1 effectué)
  ☐ Assurance active au jour de la saisie
  ☐ Cerfa 13749 signé client en votre possession
  ☐ Mandat 13757 signé client en votre possession
```

---

## 4. Modèle économique SaaS

Pas d'opérateur = coût très faible = marge très élevée.

| Poste | Coût plateforme | Tarification pro | Notes |
|-------|----------------|-----------------|-------|
| Phase 0 (HistoVec, VO) | 0€ | Inclus | Gratuit. |
| Phase 1 (OCR + cohérence) | 0.15 - 0.50€ | GRATUIT pro | Absorbé. |
| Phase 2 : KYC | 0.50 - 2€ | Inclus honoraires | Systématique. |
| Phase 2 : Opérateur | **0€** | N/A | **PAS D'OPÉRATEUR. Le pro soumet.** |
| **TOTAL par dossier abouti** | **0.70 - 2.50€** | **10 - 25€/dossier** | **Marge : 7.50 - 24.30€ — TRÈS HAUTE** |
| Dossier abandonné Phase 1 | 0.15 - 0.50€ | 0€ | Perte minimale. |
| Taxes CG | Le pro paie dans son propre SIV | — | Pas notre problème. |
| Honoraires | Pré-auth CB au GO. Débit sur aboutis. | 10-25€/dossier ou abo 50-150€/mois + tarif réduit | |
