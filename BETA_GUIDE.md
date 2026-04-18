# Imatra — Guide bêta agent SIV

Logiciel local de préparation des dossiers carte grise pour agents habilités SIV.
Version bêta 2.0.0-local — destinée à validation par un agent en conditions réelles.

---

## 1. Installation

### Pré-requis

- **Docker Desktop** installé et démarré → https://www.docker.com/products/docker-desktop/
- 4 Go de RAM libres
- 10 Go d'espace disque
- Connexion Internet uniquement pour le premier build (téléchargement des modèles OCR PaddleOCR)

### Étapes

1. Décompresser le ZIP `imatra-test.zip` quelque part de durable (pas le bureau).
2. Ouvrir un terminal dans le dossier `nouveau_projet`.
3. Lancer :
   - **macOS / Linux** : `bash install.sh`
   - **Windows** : double-cliquer `install.bat`
4. Attendre 5 à 15 min au premier lancement (build de l'image + téléchargement modèles OCR français ~100 Mo).
5. Quand le terminal affiche `Imatra local prêt sur http://0.0.0.0:8001`, ouvrir un navigateur sur :

   **http://localhost:8001**

### Vérification

- L'interface React s'affiche avec une sidebar (Tableau de bord, Dossiers, Clients, Paramètres).
- En haut, une bannière jaune indique "Mode essai gratuit — il vous reste 30 jour(s) et 10 dossier(s)".

### Arrêt / redémarrage

```bash
docker compose down       # arrêter
docker compose up -d      # redémarrer (sans rebuild)
```

Le dossier `data/` contient ta base SQLite, tes documents et ta licence.
**Ne pas le supprimer** sauf désinstallation totale.

---

## 2. Premier paramétrage (5 min)

Avant de pouvoir traiter un dossier, complète **Paramètres** :

1. **Profil de l'agent** : raison sociale, SIRET, email, nom commerce, adresse,
   code postal, ville, **n° d'habilitation SIV**.
2. **Cachet (avec signature dessus)** : scanne ton tampon professionnel
   AVEC ta signature manuscrite apposée par-dessus, en PNG ou JPG.
   C'est ce visuel unique qui sera apposé sur les Cerfa générés.
3. Cliquer **Enregistrer** → tu dois voir "✓ Profil complet" en vert.

Tant que ce paramétrage n'est pas terminé, le drag & drop d'email est bloqué.

---

## 3. Parcours type — du mail client au Cerfa

### Étape 1 — Réception du mail client

Ton client t'envoie un mail avec ses pièces (CNI, permis, carte grise barrée,
certificat de cession 15776, justificatif de domicile, etc.).

### Étape 2 — Glisser-déposer dans Imatra

Plusieurs options selon ton client mail :

- **Outlook / Apple Mail / Thunderbird** : glisser le mail entier vers le bureau
  (ça crée un `.eml` ou `.msg`) puis le glisser dans la zone bleue d'Imatra.
- **Gmail web** : ouvrir le mail → ⋮ → "Télécharger le message" (`.eml`) →
  glisser le `.eml` dans Imatra.
- **Sans mail** : glisser directement les PDF/JPG/PNG des pièces.

### Étape 3 — Traitement automatique

Imatra :

1. Parse le mail et extrait toutes les pièces jointes
2. Lance l'OCR PaddleOCR sur chaque pièce (5–15 sec/pièce, plus lent au 1er run)
3. Classifie automatiquement (CNI / permis / COC / facture / cession / …)
4. Extrait les données structurées (nom, prénom, date naissance, VIN, immat, …)
5. Crée un dossier draft visible dans **Tableau de bord → Dossiers récents**

### Étape 4 — Diagnostic tri-couleur

Cliquer sur le dossier → bouton **Lancer le diagnostic**. Imatra applique :

- 38 règles V-XX (validation par document)
- 21 règles C-XX (cross-checks entre documents)

Trois résultats possibles :

| Couleur | Signification | Action |
|---|---|---|
| 🟢 **VERT** | Aucun blocage, aucun warning | Cerfa générable immédiatement |
| 🟠 **ORANGE** | Warnings non bloquants | Revue agent, génération possible |
| 🔴 **ROUGE** | Au moins 1 blocage | Email de relance client requis |

### Étape 5a — Si VERT : génération du Cerfa

Bouton **Générer le Cerfa** → en 1 à 3 secondes, Imatra produit le PDF
Cerfa 13749 (VN) ou 13750 (VO) **pré-rempli avec ton cachet**.

Une modale d'archivage s'ouvre : rappel des **5 ans** d'archivage légal
(R322-9 du Code de la route) avec bouton direct vers le ZIP enrichi
(documents + Cerfa + manifest XML + SHA256SUMS pour preuve d'intégrité).

### Étape 5b — Si ROUGE : email de relance

Bouton **Email de relance** → modale avec sujet et corps pré-rédigés en français,
listant chaque blocage avec une explication claire pour le client. Bouton
**Copier dans le presse-papier** → tu colles dans Gmail/Outlook et tu envoies.

### Étape 6 — Soumission au SIV

Tu ouvres le portail SIV dans ton navigateur, tu colles ton n° de dossier
dans l'extension Imatra (à installer une fois, voir section 5), elle pré-remplit
automatiquement le formulaire SIV avec les données extraites. Tu vérifies,
tu valides, tu joins les documents et le Cerfa, tu soumets.

### Étape 7 — Cleanup RGPD automatique

Après génération du Cerfa, Imatra **supprime automatiquement** les données
sensibles (téléphone, email, prénom du client, fichiers documents). Seul
le nom est conservé 5 ans pour archivage légal.

---

## 4. Liste des fonctionnalités

### Backend

- ✅ OCR local PaddleOCR français (zéro cloud)
- ✅ Classification automatique 13 types de documents
- ✅ Extraction structurée par type
- ✅ 38 règles V-XX de validation
- ✅ 21 règles C-XX de cross-check inter-documents
- ✅ Diagnostic tri-couleur VERT / ORANGE / ROUGE
- ✅ Détection fraude (incohérence dates, identités, VIN)
- ✅ Génération Cerfa 13749 (VN) **100% PIL local**
- ✅ Génération Cerfa 13750 (VO) **100% PIL local**
- ✅ Génération de 28 templates d'emails de relance personnalisés
- ✅ Cleanup RGPD automatique post-Cerfa
- ✅ Stockage chiffré Fernet (AES-128)
- ✅ Licence cryptographique Ed25519 + mode hors-ligne 30 jours
- ✅ Mises à jour des règles V-XX/C-XX par bundle signé
- ✅ Export ZIP enrichi (manifest XML + SHA256SUMS)

### Interface agent

- ✅ Tableau de bord avec drag & drop d'emails
- ✅ Liste des dossiers avec filtres
- ✅ Vue détail dossier (documents, diagnostic, blocages)
- ✅ Génération Cerfa en un clic
- ✅ Email de relance pré-rédigé copiable presse-papier
- ✅ **Base clients récurrents** (CRUD, recherche, particuliers + personnes morales)
- ✅ Paramètres : profil agent, upload cachet, activation licence, mises à jour règles
- ✅ Rappel UI archivage 5 ans après génération Cerfa
- ✅ Bannière de licence (essai / licencié / expiré)

### Extension navigateur SIV (Manifest v3)

- ✅ Pré-remplissage automatique du portail SIV depuis un dossier Imatra
- ✅ Compatible Chrome / Edge
- ✅ Aucune donnée envoyée hors de ta machine

---

## 5. Extension navigateur (optionnel pour ce test)

Voir [extension/README.md](extension/README.md). Installation en mode développeur
dans `chrome://extensions`. **Note** : les sélecteurs CSS du DOM SIV sont des
placeholders, à calibrer sur une vraie session SIV ouverte.

---

## 6. Limites connues de cette bêta

⚠️ Ces points sont à valider avec ton retour terrain :

- **Cerfa 13749 / 13750** : positions pixel calibrées sur les modèles 2025,
  mais à vérifier visuellement sur tes premiers Cerfa générés.
- **Sélecteurs extension SIV** : non calibrés sur le vrai DOM (placeholders).
- **OCR PaddleOCR** : très bon mais peut se tromper sur des scans de mauvaise
  qualité ou des photos prises de travers — vérifier les données extraites
  avant de générer le Cerfa.
- **Pas de mode multi-agent** : un seul profil par installation Docker.

---

## 7. Sécurité et conformité

- 🔒 **Aucun appel cloud** : zéro Google, Anthropic, AWS, Twilio, Stripe, etc.
- 🔒 **Aucune donnée client ne quitte ta machine** — l'éditeur ne traite rien.
- 🔒 **Stockage chiffré Fernet** sur tous les documents.
- 🔒 **Licence Ed25519** vérifiée 100% en local.
- 🔒 **RGPD** : tu es seul sous-traitant de tes clients. L'éditeur Imatra
  est un fournisseur de logiciel, pas un sous-traitant RGPD.

---

## 8. Retours attendus

Ce que je veux savoir après tes premiers dossiers réels :

1. **Le drag & drop fonctionne sur tes vrais mails clients ?**
2. **L'OCR extrait correctement les bonnes données ?** (sinon : quelle pièce, quel champ)
3. **Le diagnostic VERT/ORANGE/ROUGE est-il pertinent ?** (faux positifs ? faux négatifs ?)
4. **Le Cerfa généré est-il accepté tel quel par le SIV ?** (positions OK ? cachet bien placé ?)
5. **Les emails de relance sont-ils utilisables tels quels ?**
6. **Qu'est-ce qui te manque dans l'interface ?** (champs, boutons, raccourcis)
7. **Combien de temps gagnes-tu vs ton process actuel ?**

Tout retour, même négatif, est précieux. Merci pour le test 🙏
