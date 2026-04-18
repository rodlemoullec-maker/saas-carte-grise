# Scénario E2E — Imatra local

Ce document décrit le **scénario de test bout-en-bout** à exécuter manuellement
sur une installation Docker complète d'Imatra avant chaque release.

Les tests automatisés (251 tests pytest) couvrent les modules unitaires et
d'intégration. Ce scénario E2E couvre le **flow complet** depuis l'installation
jusqu'à la génération du Cerfa, en conditions réelles avec le moteur PaddleOCR.

---

## Pré-requis

- Une machine Linux/macOS/Windows avec **Docker Desktop** installé
- 4 Go de RAM disponibles pour Docker
- 10 Go d'espace disque libre
- Une connexion internet (pour le premier build de l'image — installation des modèles PaddleOCR)
- Un échantillon de documents de test (CNI, permis, COC, facture, justificatif de domicile)

---

## Étape 1 — Installation propre

```bash
# Cloner le repo (ou copier les fichiers fournis)
git clone <repo-url> imatra-test
cd imatra-test

# Lancer l'installation
bash install.sh   # Linux/macOS
# OU
install.bat       # Windows
```

**Vérifications attendues :**
- ✅ Docker est détecté et démarré
- ✅ Build de l'image en 5-15 minutes au premier lancement
- ✅ PaddleOCR télécharge les modèles français (~100 Mo)
- ✅ Container démarre, healthcheck OK en moins de 60 secondes
- ✅ `http://localhost:8001/health` répond `{"status": "ok", "ocr_provider": "paddle"}`
- ✅ `http://localhost:8001/info` retourne les métadonnées Imatra

---

## Étape 2 — Premier accès et configuration agent

1. Ouvrir `http://localhost:8001` dans un navigateur
2. **Vérifier** : la page affiche l'interface React (sidebar + tableau de bord)
3. **Vérifier** : la bannière de licence indique "Mode essai gratuit — il vous reste 30 jour(s) et 10 dossier(s)"
4. Aller dans **Paramètres**
5. Renseigner le profil agent :
   - Raison sociale : `Cabinet Test SIV`
   - SIRET : `12345678901234`
   - Email : `test@example.fr`
   - Nom commerce : `Cabinet Test SIV`
   - Adresse : `12 rue de la Paix`
   - Code postal : `75001`
   - Ville : `Paris`
   - Numéro habilitation : `TEST-12345`
6. Cliquer sur **Enregistrer**
7. **Vérifier** : `setup_complete: false` car cachet et signature manquants
8. **Vérifier** : la section Licence affiche "Mode essai"
9. **Vérifier** : la section Règles affiche `version: 2026.04.01 (default)`

---

## Étape 3 — Test du drag & drop d'email

1. Créer un fichier `test.eml` minimal avec une pièce jointe PDF de CNI :
   ```
   From: marie.dupont@gmail.com
   To: agent@cabinet-test.fr
   Subject: Documents pour ma carte grise
   MIME-Version: 1.0
   Content-Type: multipart/mixed; boundary="BOUNDARY"

   --BOUNDARY
   Content-Type: text/plain; charset=utf-8

   Bonjour, voici mes documents.

   --BOUNDARY
   Content-Type: application/pdf; name="cni.pdf"
   Content-Disposition: attachment; filename="cni.pdf"
   Content-Transfer-Encoding: base64

   <base64 d'une vraie CNI scannée>
   --BOUNDARY--
   ```

2. Aller dans le **Tableau de bord**
3. Glisser le fichier `test.eml` dans la zone bleue
4. **Vérifier** : un spinner apparaît avec le message "Lecture de l'email et OCR en cours…"
5. **Vérifier** : après 5-15 secondes, le système :
   - Crée un dossier draft (référence `CG-2026-XXXXX`)
   - Extrait le texte de la CNI via PaddleOCR
   - Classifie le document comme `CNI`
   - Extrait le nom, prénom, date de naissance
6. **Vérifier** : le dossier apparaît dans la liste "Dossiers récents"

---

## Étape 4 — Test du diagnostic

1. Cliquer sur le dossier nouvellement créé
2. **Vérifier** : la vue détail affiche :
   - Référence du dossier
   - Nom du client extrait
   - Statut PENDING ou DIAGNOSTIC
3. Glisser des documents complémentaires (permis, COC, facture, justificatif de domicile)
4. Cliquer sur **Lancer le diagnostic**
5. **Vérifier** : le diagnostic s'affiche en VERT, ORANGE ou ROUGE selon les blocages détectés
6. **Vérifier** : la liste des blocages (codes V-XX) apparaît si ROUGE

---

## Étape 5 — Test génération du Cerfa (100% PIL local)

1. Sur un dossier en VERT, cliquer sur **Générer le Cerfa**
2. **Vérifier** : génération en 1-3 secondes (PIL pur, pas d'appel cloud)
3. **Vérifier** : le PDF Cerfa 13749 (VN) ou 13750 (VO) est créé dans `data/documents/{dossier_id}/cerfa/`
4. Cliquer sur **Télécharger ZIP**
5. **Vérifier** : le ZIP contient tous les documents + le Cerfa généré
6. **Vérifier** : aucune connexion à `service-public.gouv.fr` n'est effectuée
   (lancer `tcpdump` ou un firewall en mode bloquant pour confirmer)

---

## Étape 6 — Test email de relance

1. Sur un dossier en ROUGE avec plusieurs blocages, cliquer sur **Email de relance**
2. **Vérifier** : une modal s'ouvre avec :
   - Sujet pré-rempli : `Carte grise XXX (CG-2026-XXXXX) — N éléments à compléter`
   - Corps personnalisé avec le prénom du client
   - Liste numérotée des blocages avec titre + explication claire
   - Signature complète de l'agent (nom, adresse, téléphone, email)
3. Cliquer sur **Copier dans le presse-papier**
4. **Vérifier** : le texte est copié et peut être collé dans Gmail/Outlook
5. **Vérifier** : aucun email n'est envoyé par le logiciel — tout est manuel

---

## Étape 7 — Test du système de licences

### 7a. Génération d'une licence de test

```bash
# UNE SEULE FOIS — générer la paire de clés Ed25519
docker compose exec imatra python scripts/generate_license_keypair.py
# → copier la clé publique dans engine/license/signer.py PUBLIC_KEY_HEX
# → rebuild l'image : docker compose up -d --build

# Générer une licence client
docker compose exec imatra python scripts/generate_license.py \
  --email test@example.fr \
  --name "Cabinet Test SIV" \
  --type annual \
  --private-key <hex>
```

### 7b. Activation dans l'interface

1. Aller dans **Paramètres → Licence**
2. Coller le token généré dans le champ d'activation
3. Cliquer sur **Activer**
4. **Vérifier** : message "Licence activée pour Cabinet Test SIV"
5. **Vérifier** : la bannière du haut disparaît (mode `licensed`)
6. **Vérifier** : `data/.license/license.key` existe avec permissions 600

### 7c. Test mode hors-ligne

1. Couper internet (ou bloquer `licenses.imatra.fr` au firewall)
2. Redémarrer le container : `docker compose restart`
3. **Vérifier** : Imatra démarre normalement
4. **Vérifier** : la licence reste active (vérification cryptographique locale)
5. **Vérifier** : aucune erreur dans les logs Docker

---

## Étape 8 — Test mises à jour des règles

1. Vérifier la version actuelle : aller dans **Paramètres → Règles**
2. **Vérifier** : `version: 2026.04.01`, `source: default`
3. Cliquer sur **Vérifier les mises à jour**
4. **Vérifier** : message `up_to_date` ou `error` (selon que le serveur de l'éditeur est en ligne)
5. **Optionnel** : modifier `data/rules/current.json` avec un bundle signé manuellement, redémarrer
6. **Vérifier** : la version change et `source: local_signed`

---

## Étape 9 — Test du cleanup RGPD automatique

1. Créer un dossier complet avec documents client
2. Générer le Cerfa (étape 5)
3. **Vérifier** dans la BDD SQLite (`data/imatra.db`) :
   - `client_telephone`, `client_email`, `client_prenom` sont NULL
   - `client_nom` est conservé (archivage légal 5 ans)
   - Les fichiers documents sont supprimés du disque
   - Les `extracted_data` des documents contiennent `{"supprime_rgpd": true}`

---

## Étape 10 — Test de désinstallation propre

```bash
docker compose down
docker rmi imatra:local-2.0
```

**Vérifier :**
- ✅ Le container et l'image sont supprimés
- ✅ Le dossier `data/` reste intact (les données de l'agent sont préservées)
- ✅ Aucun processus résiduel

Pour réinstaller :
```bash
docker compose up -d --build
```
**Vérifier :** toutes les données reviennent (BDD, documents, licence, règles).

---

## Critères de validation globaux

| Critère | Validation |
|---|---|
| Aucun appel à un service tiers (Google, Anthropic, Twilio, Stripe) | ✅ |
| Aucun document client ne quitte la machine | ✅ |
| OCR fonctionne en local avec PaddleOCR | ✅ |
| Cerfa généré 100% en PIL (VN + VO) | ✅ |
| Diagnostic VERT/ORANGE/ROUGE cohérent | ✅ |
| Email de relance copiable dans presse-papier | ✅ |
| Licence vérifiée cryptographiquement (Ed25519) | ✅ |
| Mode hors-ligne 30 jours | ✅ |
| Cleanup RGPD automatique après Cerfa | ✅ |
| Healthcheck Docker fonctionnel | ✅ |

---

## Tests automatisés couvrant ces fonctionnalités

| Phase E2E | Tests automatisés associés |
|---|---|
| Étape 3 (drag & drop email) | `tests/unit/test_email_parser.py` (24 tests) |
| Étape 3 (matching dossier) | `tests/unit/test_dossier_matcher.py` (24 tests) |
| Étape 4 (diagnostic) | `tests/unit/test_decision_engine.py`, `test_pipeline.py`, `test_cross_checks.py` |
| Étape 6 (email relance) | `tests/unit/test_relance_emails.py` (16 tests) |
| Étape 7 (licences) | `tests/unit/test_license_signer.py` (15 tests), `test_license_manager.py` (10 tests) |
| Étape 8 (règles) | `tests/unit/test_rules_loader.py` (12 tests) |
| Routes API | `tests/unit/test_smoke.py` (vérifie les endpoints attendus + absence des obsolètes) |

**Total : 251 tests automatisés passent (0 échec, 3 skipped).**

Le scénario E2E manuel doit être exécuté **avant chaque release** sur une
machine vierge avec Docker Desktop, pour valider que tout fonctionne en
conditions réelles avec le vrai moteur PaddleOCR (que les tests unitaires
mockent par souci de rapidité).
