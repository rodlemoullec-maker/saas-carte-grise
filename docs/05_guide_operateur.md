# Guide Opérateur — Utilisation quotidienne

Ce guide décrit comment utiliser le système au quotidien,
une fois le développement terminé et le système en production.


## Démarrage du système

### Avec Docker (recommandé — production)

```bash
# Première installation
./scripts/install.sh

# Démarrage quotidien
docker compose up -d

# Arrêt
docker compose down
```

### Sans Docker (développement)

```bash
# 1. Démarrer Ollama (IA locale)
ollama serve

# 2. Démarrer PostgreSQL
brew services start postgresql@17

# 3. Démarrer le dashboard (interface opérateur)
cd carte_grise_auto
source venv/bin/activate
streamlit run dashboard/app.py

# 4. (Optionnel) Démarrer OpenClaw (agent autonome)
openclaw start
```

Le dashboard est accessible sur : http://localhost:8501


## Flux de travail quotidien

### 1. OpenClaw surveille les emails (automatique)
- OpenClaw poll la boîte email en continu
- Chaque email de la personne habilitée déclenche le workflow
- La personne habilitée reçoit un accusé réception automatique
- Aucune intervention nécessaire

### 2. Traitement autonome par OpenClaw (~30 secondes)
Pour chaque dossier, OpenClaw enchaîne automatiquement :
1. Classifie les documents (skill-classify → Qwen2.5-VL)
2. Extrait le texte par OCR (skill-ocr → Surya)
3. Structure les données en JSON (skill-extract → Qwen2.5)
4. Recherche le véhicule en BDD (skill-vehicle → PostgreSQL)
5. Vérifie la cohérence (skill-validate)
6. Calcule les taxes (skill-taxes)
7. Pré-remplit le CERFA (skill-cerfa → PDF)
8. Notifie l'opérateur (skill-notify)

**Si un document manque :** OpenClaw relance automatiquement la personne habilitée par email.
**Si une incohérence est détectée :** OpenClaw alerte l'opérateur.

### 3. Validation par l'opérateur (2-3 minutes)
Ouvrir le dashboard → sélectionner un dossier notifié "prêt" :

| Ce que vous voyez | Ce que vous faites |
|---|---|
| Documents originaux (à gauche) | Vérifier visuellement |
| Données extraites (à droite) | Corriger si erreur (champs éditables) |
| Indicateurs verts | RAS, données fiables |
| Indicateurs oranges | Vérifier — confiance moyenne |
| Indicateurs rouges | Corriger — IA peu sûre |
| Alertes cross-validation | Résoudre les incohérences |

### 4. Génération et envoi du CERFA
- Cliquer "Valider et générer CERFA"
- Le CERFA PDF pré-rempli est généré
- OpenClaw envoie automatiquement le CERFA par email à la personne habilitée
- La personne habilitée se charge de la soumission auprès de l'ANTS


## Statuts des dossiers

| Statut | Signification | Qui agit |
|---|---|---|
| `nouveau` | Email reçu, traitement lancé | OpenClaw |
| `en_cours` | IA en train d'extraire les données | OpenClaw |
| `documents_manquants` | Document absent → personne habilitée relancée | OpenClaw (auto) |
| `pret` | Extraction terminée, en attente de validation | Opérateur |
| `valide` | Opérateur a validé, CERFA généré | Opérateur |
| `envoye` | CERFA envoyé à la personne habilitée | OpenClaw (auto) |


## Documents attendus par dossier

Pour un changement de titulaire (cas le plus fréquent) :

| Document | Obligatoire | Vérifié par OpenClaw |
|---|---|---|
| Certificat d'immatriculation (carte grise) barré | Oui | VIN, immat, titulaire |
| Certificat de cession (CERFA 15776) signé | Oui | Vendeur, acheteur, date |
| CNI ou passeport de l'acheteur | Oui | Nom, validité |
| Justificatif de domicile < 6 mois | Oui | Nom, adresse, date |
| Contrôle technique < 6 mois | Si véhicule > 4 ans | Date, résultat |
| Attestation d'assurance | Oui | — |
| Mandat / procuration | Si le titulaire ne fait pas la démarche | — |


## En cas de problème

| Problème | Solution |
|---|---|
| OCR illisible | Demander au client un meilleur scan/photo |
| IA se trompe sur un champ | Corriger manuellement dans le dashboard |
| Document mal classé | Reclasser manuellement dans le dashboard |
| Véhicule non trouvé en base | Saisir manuellement le CNIT ou les données techniques |
| Email non détecté | Vérifier la connexion IMAP dans OpenClaw |
| OpenClaw ne répond plus | `openclaw restart` puis vérifier `ollama serve` |
| Ollama lent/crash | Vérifier la RAM disponible, relancer `ollama serve` |


## Commandes utiles

### Docker (production)

```bash
# Démarrer tout
docker compose up -d

# Arrêter tout
docker compose down

# Voir les logs
docker compose logs -f app

# Redémarrer l'app
docker compose restart app

# Vérifier le statut
docker compose ps
```

### Sans Docker (développement)

```bash
# Statut OpenClaw
openclaw status

# Redémarrer OpenClaw
openclaw restart

# Voir les logs OpenClaw
openclaw logs

# Vérifier Ollama
ollama list          # modèles installés
ollama ps            # modèles en cours d'exécution

# Vérifier PostgreSQL
brew services list   # statut des services
psql carte_grise     # accès direct à la BDD
```
