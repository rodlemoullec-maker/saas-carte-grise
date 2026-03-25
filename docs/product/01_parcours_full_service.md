# Parcours Full Service — Doc 1A

Cible : Pro NON habilité SIV → On gère tout
Extension navigateur semi-auto + batch
Taxes : CB pro (pas d'agrément TP) | Honoraires : pré-auth CB ou SEPA mensuel

---

## 1. Parcours VN — Véhicule Neuf (17 étapes)

Pas de DA, pas de CG barrée, pas de CT, pas de Phase 0 HistoVec.

| N° | Étape | Qui | Ce qui se passe | Si problème |
|----|-------|-----|----------------|------------|
| **PARCOURS PRO** |||||
| 1 | Vente du VN au client | Pro | Le client achète un VN (moto ou voiture) chez le pro. | |
| 2 | Vérif identité en personne **(NIV.1)** | Pro | CNI originale en main. Visage ↔ photo. Hologramme. Coche attestation dans le portail. **OBLIGATION LÉGALE (convention SIV).** | Pas coché → dossier bloqué. |
| 3 | Collecte docs client | Pro | Scan/photo : CNI recto/verso, Permis (catégorie=véhicule) — OBLIGATOIRE titulaire principal. **Exception PM : pas de permis, CNI gérant suffit. Exception co-titulaire : pas de permis requis.** Justif domicile < 6 mois, Assurance véhicule (OBLIGATOIRE, décret 2017-1278) : avec VIN (pas d'immat car VN). Attestation provisoire 1 mois acceptée. Mémo Véhicule Assuré (2025). Pas forcément au nom titulaire CG. | Si hébergé : 4 docs (D-15). Si étranger : titre séjour. Si PM : Kbis + CNI représentant. |
| 4 | Préparation docs pro | Pro | COC (constructeur), Cerfa demande CG VN (13749) — signé client, Mandat (13757) — signé client. Si Cerfa pas signés → portail génère pré-remplis. | |
| 5 | Création dossier portail | Pro | 1 dossier = 1 véhicule. Saisie VIN + nom client. Upload docs (1 fois ou au fil de l'eau). Coche attestation identité. **→ LE SYSTÈME PREND LE RELAIS.** Détection auto VN (COC présent). Le pro peut uploader plusieurs dossiers en lot. | |
| **PHASE 1 — PRÉ-QUALIFICATION (gratuit pro, ~0.50€ coût)** |||||
| 6 | Complétude | Système | Vérifie : CNI, permis (sauf PM/co-tit), justif, assurance (VIN), COC, Cerfa, mandat, attestation identité pro. Classification auto des docs uploadés. | Manquant → BLOCAGE + relance. Assurance manquante → relance spécifique (décret 2017-1278). Cerfa pas signé → génère pré-rempli. |
| 7 | OCR + extraction | Système | CNI (nom, date naissance, validité), permis (catégorie), justif (adresse, date), COC (CNIT, VIN, puissance, CO2 WLTP), assurance (VIN, validité). Score OCR. | OCR < seuil → BLOCAGE "re-scanner". Rature Cerfa → BLOCAGE. |
| 8 | Validité | Système | CNI (règle +5 ans 2004-2013), permis, justif < 6 mois, assurance en cours (VIN ↔ COC). Assurance provisoire < 7j restants → WARNING. Pas de CT (VN). | Expiré → BLOCAGE + relance. Assurance VIN ≠ COC → BLOCAGE. |
| 9 | Cohérence croisée | Système | Nom CNI ↔ Cerfa (fuzzy), CNI ↔ permis, adresse ↔ justif. VIN COC ↔ Cerfa ↔ assurance. CNIT ↔ UTAC, puissance, CO2 WLTP → malus. Permis catégorie ↔ véhicule, âge ↔ catégorie. | VIN incohérent → BLOCAGE TOTAL. Identité < 85% → ESCALADE. Mineur → ESCALADE. Permis inadapté → BLOCAGE. |
| 10 | DIAGNOSTIC + estimation taxes | Système | 🟢 VERT / 🟠 ORANGE / 🔴 ROUGE. Le pro voit le diagnostic dans son portail. **ESTIMATION TAXES affichée (indicatif) :** taxe régionale + malus + gestion 11€ + acheminement 2.76€. Calculée à partir des données extraites (puissance, CO2, dépt client). Montant exact confirmé par le SIV au moment de la soumission. | ROUGE persistant → reste Phase 1. Coût max ~0.50€. Estimation = indicative. |
| **🚦 GO / NO-GO — FACTURATION** |||||
| 11 | Le pro lance le traitement | Pro | Le pro voit VERT. Clique "Lancer le traitement". **PAIEMENT HONORAIRES :** Pré-autorisation CB du pro (enregistrée dans le portail). Montant = tes honoraires × nb dossiers lancés. Le pro n'est PAS débité maintenant. Débit uniquement quand le CPI est généré. Alternative pros à volume : facture mensuelle + prélèvement SEPA. | Pas de lancement → pas de facturation. Pré-auth expirée (7-30j) → renouveler. |
| **PHASE 2 — TRAITEMENT** |||||
| 12 | KYC anti-fraude (systématique) | Système | Vérif authenticité CNI (Ariadnext, IDnow). **NIVEAU 2 authentification.** Résultat : AUTHENTIQUE / SUSPECT / REJETÉ. AUTHENTIQUE → passage direct soumission SIV. SUSPECT → contrôle visuel opérateur (NIV.3, étape 13). REJETÉ → BLOCAGE automatique + notification pro. | SUSPECT → étape 13. REJETÉ → BLOCAGE. AUTHENTIQUE → étape 14 directement. |
| 13 | Contrôle visuel **(NIV.3) — UNIQUEMENT SI KYC SUSPECT** | Opérateur | Déclenché UNIQUEMENT si KYC = SUSPECT (~10% des dossiers). Analyse approfondie CNI (~10 min). Si doute → escalade pro "vérifiez l'original". Si frauduleux → BLOCAGE définitif. Si KYC = AUTHENTIQUE, cette étape est **SAUTÉE**. | Doute → escalade pro. Frauduleux → BLOCAGE définitif. |
| 14 | Soumission SIV (via extension navigateur) | Opérateur + Extension | L'extension pré-remplit automatiquement tous les champs du formulaire SIV. L'opérateur : 1) Vérifie les champs pré-remplis (30 sec), 2) Valide d'un clic → soumission, 3) SIV affiche montant exact des taxes, 4) Opérateur saisit CB du pro (enregistrée), 5) SIV génère le CPI, 6) Extension récupère le CPI automatiquement. **En mode BATCH :** enchaîne les dossiers automatiquement. **Pas d'interrogation SIV préalable (VN = véhicule nouveau).** **TAXES : CB du pro, débit unitaire par le SIV. On ne touche PAS aux taxes.** | Rejet SIV → motif noté, relance. CB pro refusée → notification pro. Extension : si formulaire SIV change → maintenance. Fallback : copier-coller assisté. |
| **APRÈS** |||||
| 15 | CPI + notification | Système | CPI récupéré auto par l'extension. Déposé dans le portail du pro. Notification pro + client (si autorisé). Le pro remet le CPI au client (1 mois, France). **HONORAIRES : débit de la pré-autorisation CB (dossier abouti).** | |
| 16 | CG définitive | Imprimerie Nat. | Envoyée au domicile client. 3-5 jours. Notification pro + client. | Non reçue 15j → alerte. |
| 17 | Archivage | Système | 5 ans. Coffre-fort numérique (obligatoire 2026). | |

---

## 2. Parcours VO — Véhicule Occasion (19 étapes)

Inclut Phase 0 HistoVec, DA + récépissé, CG barrée, CT, interrogation SIV.

| N° | Étape | Qui | Ce qui se passe | Si problème |
|----|-------|-----|----------------|------------|
| **PARCOURS PRO** |||||
| 1 | Vente du VO au client | Pro | Le client achète un VO du stock du pro. DA enregistrée. Récépissé DA + CG barrée disponibles. | |
| 2 | Vérif identité (NIV.1) | Pro | Idem VN. CNI originale, visage, hologramme, attestation portail. | |
| 3 | Collecte docs client | Pro | Idem VN sauf assurance : immat existante OU VIN. Permis : mêmes exceptions (PM, co-titulaire). | |
| 4 | Préparation docs pro | Pro | CG barrée (vendu le + date + heure + signature), Récépissé DA, Cerfa cession (15776) — tampon SIRET, Cerfa demande CG VO (13750), Mandat (13757), CT < 6 mois si voiture > 4 ans / moto > 5 ans. **CT non requis si < 4 ans (voit) / < 5 ans (moto). CT volontaire sur dispensé → DEVIENT obligatoire.** | |
| 5 | Création dossier portail | Pro | Saisie immat + nom client. Upload docs. Détection auto VO (CG barrée présente). Upload en lot possible. | |
| **PHASE 0 — HISTOVEC (gratuit, VO uniquement)** |||||
| 6 | Consultation HistoVec / CSA | Système | Dès saisie immat → consultation auto. Gage, OTCI, vol, VEC/VEI, historique, CT, km. **GRATUIT.** | Gage/OTCI/vol → STOP + notif pro. VEC/VEI → WARNING. |
| **PHASE 1 — PRÉ-QUALIFICATION (gratuit pro)** |||||
| 7 | Complétude | Système | CNI, permis (sauf PM/co-tit), justif, assurance, CG barrée, récépissé DA, Cerfa cession, Cerfa CG, mandat, CT si requis, attestation identité pro. | Idem VN + DA/récépissé manquant → relance pro. |
| 8 | OCR + extraction | Système | Idem VN + CG barrée (VIN, immat, titulaire, date/heure, n° formule), CT (date, résultat, immat), Cerfa cession (vendeur, acheteur, VIN), récépissé DA (VIN, SIREN pro). | Idem VN. |
| 9 | Validité | Système | Idem VN + CT < 6 mois à DATE SAISIE SIV, contre-visite < 2 mois, code cession < 15j, assurance immat/VIN ↔ véhicule. | CT 5-6 mois → WARNING. CT défavorable critique → BLOCAGE TOTAL. |
| 10 | Cohérence croisée | Système | Idem VN + : VIN identique sur TOUS docs (incl. DA, récépissé DA, CT, cession). Vendeur DA = titulaire CG. Vendeur cession = pro. Dates CG barrée ↔ DA ↔ cession. Nb signatures ↔ co-titulaires CG. | Vendeur DA ≠ titulaire CG → ESCALADE. Heure absente CG barrée → BLOCAGE. Signature co-tit manquante → BLOCAGE. |
| 10b | Analyse CG barrée | Système | Barre diag, "vendu le" + date + heure, signature(s), n° formule. | Non barrée → BLOCAGE. Heure/signature manquante → BLOCAGE. |
| 11 | DIAGNOSTIC + estimation taxes | Système | 🟢/🟠/🔴 + estimation taxes indicative. Pro voit tout dans son portail. | Idem VN. |
| **🚦 GO / NO-GO — FACTURATION** |||||
| 12 | Le pro lance le traitement | Pro | Idem VN. Pré-autorisation CB honoraires. Alternative SEPA mensuel. | Idem VN. |
| **PHASE 2 — TRAITEMENT** |||||
| 13 | Interrogation SIV | Opérateur + Extension | L'extension pré-remplit la requête d'interrogation. Confirme statut SIV (gage, OTCI, vol) en temps réel. Vérifie que rien n'a changé depuis Phase 0. | Anomalie → BLOCAGE CRITIQUE + notif pro. |
| 14 | KYC anti-fraude (systématique) | Système | Idem VN. NIV.2. Déclenché APRÈS interrogation SIV. AUTHENTIQUE → soumission SIV directe. SUSPECT → étape 15. REJETÉ → BLOCAGE. | Idem VN. |
| 15 | Contrôle visuel (NIV.3) — UNIQUEMENT SI SUSPECT | Opérateur | Idem VN. Déclenché uniquement si SUSPECT. Sauté si AUTHENTIQUE. | Idem VN. |
| 16 | Soumission SIV (via extension navigateur) | Opérateur + Extension | Idem VN sauf : changement de titulaire (pas 1ère immat). Même flux extension : pré-remplissage → vérif 30 sec → clic → montant taxes exact → CB pro → CPI → dossier suivant. Batch identique. | Idem VN. |
| **APRÈS** |||||
| 17 | CPI + notification | Système | Idem VN. CPI récupéré auto. Débit honoraires. | |
| 18 | CG définitive | Imprimerie Nat. | Idem VN. | |
| 19 | Archivage | Système | Idem VN. | |

---

## 3. Authentification identité — 3 niveaux

| Niveau | Qui | Quand & quoi | Si problème |
|--------|-----|-------------|------------|
| **NIV.1 — Pro sur place** | Pro | Étape 2. CNI originale, visage ↔ photo, hologramme. Atteste portail. | Pas coché → bloqué. Resp. légale pro. |
| **NIV.2 — Système** | Système | Phase 1 : OCR + croisements. Phase 2 : KYC systématique (Ariadnext/IDnow). | Incohérence → BLOCAGE. KYC suspect → ESCALADE. KYC rejeté → BLOCAGE. |
| **NIV.3 — Opérateur (CONDITIONNEL)** | Opérateur | Phase 2 : UNIQUEMENT si KYC = SUSPECT. Analyse approfondie CNI (~10 min). **~90% des dossiers ne déclenchent pas le NIV.3.** Si KYC = AUTHENTIQUE → étape sautée. | Doute → escalade pro. Frauduleux → BLOCAGE. |

---

## 4. Modèle économique Full Service

Agent habilité sans agrément TP. Taxes payées par le pro via sa CB.

| Poste | Coût plateforme | Tarification pro | Notes |
|-------|----------------|-----------------|-------|
| Phase 0 (HistoVec, VO) | 0€ | Inclus | Gratuit. |
| Phase 1 (OCR + cohérence) | 0.15 - 0.50€ | GRATUIT pro | Absorbé. Fidélisation. |
| Phase 2 : KYC | 0.50 - 2€ | Inclus honoraires | Systématique. |
| Phase 2 : Opérateur + extension | 1 - 2€ (~3 min/dossier) | Inclus honoraires | NIV.3 uniquement ~10% dossiers. |
| **TOTAL par dossier abouti** | **2 - 5€** | **30 - 60€/dossier** | **Marge : 25 - 58€** |
| Dossier abandonné Phase 1 | 0.15 - 0.50€ | 0€ | Perte minimale. |
| Dossier bloqué Phase 0 | 0€ | 0€ | Aucune perte. |
| Taxes CG → État | CB du pro, débit unitaire SIV | — | On ne touche PAS aux taxes. |
| Honoraires | Pré-auth CB au GO, débit sur CPI | 30-60€/dossier ou abo | Pré-auth : 7-30j validité. |
| Cas escalade | Variable | Devis : 60-150€ | Import, succession, tutelle, double cession. |
