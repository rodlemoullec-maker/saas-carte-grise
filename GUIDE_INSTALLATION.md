# Guide d'installation — Carte Grise Auto

Ce guide t'explique **pas à pas** comment installer et lancer le système
sur ton Mac Studio. Aucune connaissance technique n'est requise.

---

## Prérequis

- Mac Studio avec puce Apple Silicon (M1/M2/M3/M4)
- 32 GB de RAM
- macOS à jour
- Connexion internet (pour le téléchargement initial)
- Un compte email (Gmail, Outlook, ou autre) dédié à la réception des dossiers


---


## Étape 1 — Recevoir et décompresser le dossier

Tu as reçu un fichier `carte_grise_auto.zip` (par email, clé USB, WeTransfer, etc.).

1. **Double-clique** sur `carte_grise_auto.zip` pour le décompresser
   - macOS le décompresse automatiquement dans le même dossier
   - Tu obtiens un dossier `carte_grise_auto/`

2. **Déplace ce dossier** dans tes Documents :
   - Ouvre le Finder
   - Fais glisser `carte_grise_auto/` dans le dossier **Documents** à gauche
   - Le chemin final doit être : `/Users/TON_NOM/Documents/carte_grise_auto/`

3. **Vérifie** en ouvrant le dossier qu'il contient bien :
   ```
   carte_grise_auto/
   ├── config/
   ├── dashboard/
   ├── data/
   ├── docs/
   ├── scripts/          ← contient install.sh
   ├── skills/
   ├── src/
   ├── templates/
   ├── tests/
   ├── GUIDE_INSTALLATION.md   ← ce fichier
   └── requirements.txt
   ```


---


## Étape 2 — Installer Visual Studio Code (optionnel mais recommandé)

VS Code est un éditeur de code **gratuit** qui te permettra de voir les
fichiers du projet et d'utiliser le terminal intégré.

1. Va sur : **https://code.visualstudio.com/**
2. Clique **"Download for Mac"** (Universal ou Apple Silicon)
3. Ouvre le fichier téléchargé (.zip) → un fichier `Visual Studio Code.app` apparaît
4. Glisse-le dans ton dossier **Applications**
5. Ouvre VS Code
6. **Ouvre le projet** : menu Fichier → "Ouvrir un dossier..." → Documents → carte_grise_auto → Ouvrir
7. Tu vois maintenant tous les fichiers du projet à gauche

**Pour ouvrir le terminal dans VS Code :**
- Menu : Terminal → Nouveau Terminal
- Ou raccourci : Ctrl + ` (la touche backtick, en haut à gauche du clavier)

Le terminal s'ouvre **directement dans le bon dossier** — pas besoin de
taper `cd`. C'est plus pratique que le Terminal séparé.

> Si tu ne veux pas installer VS Code, tu peux utiliser le **Terminal**
> natif du Mac (voir ci-dessous).


---


## Étape 3 — Ouvrir le Terminal

### Option A : Terminal dans VS Code (si installé)

Si tu as installé VS Code à l'étape 2 :
1. Ouvre VS Code avec le projet (s'il n'est pas déjà ouvert)
2. Menu : Terminal → Nouveau Terminal
3. Le terminal est déjà dans le bon dossier → passe à l'étape 4

### Option B : Terminal natif du Mac

1. Ouvre l'application **Terminal** sur ton Mac :
   - Spotlight : appuie sur **Cmd + Espace** → tape "Terminal" → Entrée
   - Ou : Finder → Applications → Utilitaires → Terminal

2. Va dans le dossier du projet en tapant cette commande puis Entrée :
   ```bash
   cd ~/Documents/carte_grise_auto
   ```

3. Vérifie que tu es au bon endroit :
   ```bash
   ls scripts/install.sh
   ```
   - Si ça affiche `scripts/install.sh` → c'est bon, passe à l'étape 4
   - Si ça affiche "No such file" → tu n'es pas dans le bon dossier,
     vérifie que le dossier est bien dans Documents


---


## Étape 3 — Lancer l'installation

```bash
./scripts/install.sh
```

Si tu vois "permission denied", tape d'abord :
```bash
chmod +x scripts/install.sh scripts/setup_openclaw.sh
./scripts/install.sh
```

### Ce qui va se passer automatiquement :

Le script va installer et configurer tout ce qu'il faut. C'est long la
première fois (20-40 minutes selon ta connexion internet).

```
✓ Homebrew           — gestionnaire de paquets Mac
✓ Python             — langage de programmation
✓ Node.js            — pour OpenClaw
✓ PostgreSQL         — base de données
✓ Ollama             — serveur IA local
✓ Dépendances Python — bibliothèques du projet
✓ Base de données    — création des tables
✓ Base types mines   — données véhicules (84 000+ modèles)
✓ Modèles IA         — téléchargement (environ 10 GB)
✓ OpenClaw           — agent autonome
```

### Pendant l'installation, le script te posera 3 questions :

**Question 1 : "Serveur IMAP"**
```
Serveur IMAP (ex: imap.gmail.com) :
```
- Si tu utilises Gmail : tape `imap.gmail.com`
- Si Outlook/Hotmail : tape `outlook.office365.com`
- Si autre : demande à ton fournisseur email

**Question 2 : "Adresse email"**
```
Adresse email :
```
Tape l'adresse email qui recevra les dossiers des personnes habilitées.
Exemple : `cartegrise.auto@gmail.com`

**Question 3 : "Mot de passe application"**
```
Mot de passe application :
```
⚠️ Ce n'est **PAS** ton mot de passe email habituel.

Pour Gmail, il faut créer un "mot de passe d'application" :
1. Va sur https://myaccount.google.com/apppasswords
2. Connecte-toi à ton compte Google
3. Nom de l'application : tape "Carte Grise Auto"
4. Clique "Créer"
5. Google te donne un mot de passe de 16 caractères (ex: `abcd efgh ijkl mnop`)
6. Copie-colle ce mot de passe dans le terminal (les caractères ne s'affichent pas, c'est normal)

Pour Outlook : https://support.microsoft.com/fr-fr/account-billing/app-passwords

### Fin de l'installation

Quand tu vois :
```
============================================
  Installation terminée !
============================================
```
C'est prêt. Tu n'auras plus jamais à refaire cette étape.


---


## Étape 4 — Démarrer le système

Chaque jour, pour démarrer le système, ouvre le Terminal et tape :

```bash
cd ~/Documents/carte_grise_auto
source venv/bin/activate
streamlit run dashboard/app.py
```

Tu verras :
```
  You can now view your Streamlit app in your browser.

  Local URL: http://localhost:8501
  Network URL: http://192.168.1.XX:8501
```

**Ouvre ton navigateur** (Safari ou Chrome) et va sur :
```
http://localhost:8501
```

Le dashboard s'affiche. Tu es prêt à travailler.


---


## Étape 5 — Utilisation quotidienne

### Traiter un nouveau dossier

1. Dans le dashboard, clique sur **"Nouveau traitement"** dans le menu à gauche

2. Clique sur **"Browse files"** et sélectionne les documents du dossier :
   - Photo/scan de la carte grise
   - Photo/scan de la CNI
   - Photo/scan du certificat de cession
   - Photo/scan du justificatif de domicile
   - (Photo/scan du contrôle technique si nécessaire)

3. Clique sur **"Lancer le traitement"**

4. Attends ~30 secondes. Le système :
   - Identifie chaque document automatiquement
   - Extrait toutes les données (noms, VIN, immatriculation, etc.)
   - Recherche les caractéristiques du véhicule
   - Vérifie la cohérence entre les documents
   - Calcule les taxes
   - Génère le CERFA 13750 pré-rempli

5. Résultat :
   - **Vert "Succès"** → le dossier est prêt, va dans "Dossiers" pour valider
   - **Orange "Incomplet"** → il manque un document ou il y a une incohérence

### Valider un dossier

1. Clique sur **"Dossiers"** dans le menu à gauche

2. Sélectionne le filtre **"A valider"**

3. Clique sur le dossier pour l'ouvrir

4. Vérifie :
   - Les documents originaux (images affichées)
   - Les données extraites (à droite) — corrige si une erreur
   - Les taxes calculées
   - Les alertes éventuelles (rouge = erreur, orange = attention)

5. Si tout est bon, clique sur **"Valider le dossier"**

6. Clique sur **"Télécharger le CERFA 13750"** pour récupérer le PDF

7. Envoie le PDF par email à la personne habilitée


---


## Étape 6 — Accéder depuis ton portable

### Même réseau WiFi

1. Note l'adresse **Network URL** affichée au démarrage de Streamlit :
   ```
   Network URL: http://192.168.1.42:8501
   ```

2. Sur ton portable, ouvre le navigateur et tape cette adresse

3. Le dashboard s'affiche — tu peux travailler depuis ton portable

### Depuis un autre réseau (en déplacement)

Pour accéder au Mac Studio depuis n'importe où, installe **Tailscale**
(gratuit, 2 minutes) :

**Sur le Mac Studio :**
```bash
brew install tailscale
```
Puis ouvre Tailscale et connecte-toi avec un compte Google/Apple/GitHub.

**Sur ton portable :**
- Va sur https://tailscale.com/download
- Installe et connecte-toi avec le **même compte**

Tailscale donne une IP fixe à chaque machine (ex: `100.64.0.1`).
Tape `http://100.64.0.1:8501` dans le navigateur du portable → dashboard.


---


## Arrêter le système

Dans le Terminal, appuie sur **Ctrl+C** pour arrêter Streamlit.

Pour tout arrêter proprement :
```bash
# Arrêter PostgreSQL
brew services stop postgresql@17

# Arrêter Ollama
pkill ollama
```


---


## Relancer après un redémarrage du Mac

Après un redémarrage du Mac Studio, il faut relancer les services :

```bash
# 1. Démarrer PostgreSQL
brew services start postgresql@17

# 2. Démarrer Ollama
ollama serve &

# 3. Attendre 5 secondes que tout démarre
sleep 5

# 4. Lancer le dashboard
cd ~/Documents/carte_grise_auto
source venv/bin/activate
streamlit run dashboard/app.py
```

**Astuce** : Tu peux créer un raccourci. Crée un fichier `start.sh` :
```bash
cd ~/Documents/carte_grise_auto
cat > start.sh << 'EOF'
#!/bin/bash
brew services start postgresql@17
ollama serve &
sleep 5
source venv/bin/activate
streamlit run dashboard/app.py
EOF
chmod +x start.sh
```

Ensuite pour démarrer, tape juste :
```bash
cd ~/Documents/carte_grise_auto
./start.sh
```


---


## Résolution de problèmes

| Problème | Solution |
|---|---|
| "command not found: streamlit" | Tape `source venv/bin/activate` avant |
| "connection refused" sur le dashboard | PostgreSQL ou Ollama n'est pas démarré. Relance-les (voir section "Relancer") |
| Le traitement est très long (> 2 min) | Normal au premier lancement — Ollama charge le modèle IA en mémoire. Les suivants seront rapides (~30s) |
| "IMAP login failed" | Vérifie le mot de passe application dans le fichier `.env` |
| Le portable ne peut pas accéder au dashboard | Vérifie que les 2 machines sont sur le même WiFi. Essaie avec l'IP directement |
| "No module named ..." | Relance `source venv/bin/activate && pip install -r requirements.txt` |
| L'IA se trompe sur un champ | Corrige manuellement dans le dashboard avant de valider |
| Le CERFA est mal aligné | Les coordonnées des champs sont à calibrer — voir `src/cerfa/filler.py` |

### Modifier la configuration email

Si tu changes d'adresse email :
```bash
cd ~/Documents/carte_grise_auto
nano .env
```
Modifie les lignes IMAP_SERVER, IMAP_USER, IMAP_PASSWORD, puis relance Streamlit.

### Voir les logs en cas d'erreur

```bash
# Logs Ollama
cat ~/.ollama/logs/server.log

# Logs PostgreSQL
cat /opt/homebrew/var/log/postgresql@17.log
```


---


## Mises à jour

### Ce qui se met à jour automatiquement

- **Base véhicules** : chaque véhicule traité (moto, remorque, voiture) qui
  n'est pas dans la base est automatiquement sauvegardé. La base s'enrichit
  au fur et à mesure de l'utilisation.

### Ce qui doit être mis à jour manuellement

Les **barèmes de taxes** changent chaque année (généralement au 1er janvier) :
- Tarifs régionaux (€/CV par région)
- Barème malus CO2 (seuils et montants)
- Barème malus masse (seuil en kg)
- Taxe fixe Y6

**Pour vérifier et mettre à jour, lance :**
```bash
cd ~/Documents/carte_grise_auto
source venv/bin/activate
./scripts/update.sh
```

Ce script :
1. Télécharge les nouveaux modèles de véhicules (ADEME)
2. Met à jour les modèles IA si une nouvelle version est disponible
3. Met à jour les dépendances Python
4. **Vérifie les barèmes de taxes** et t'alerte si ils sont périmés
5. Affiche les statistiques de la base

Si les barèmes sont périmés, le script t'indique quoi modifier et où
trouver les nouveaux tarifs (liens service-public.fr).

**Fréquence recommandée :** 1 fois par mois, et obligatoirement en janvier
après la publication des nouveaux barèmes.


---


## Résumé des commandes

| Action | Commande |
|---|---|
| **Installer** (1 seule fois) | `./scripts/install.sh` |
| **Démarrer** | `source venv/bin/activate && streamlit run dashboard/app.py` |
| **Arrêter** | Ctrl+C dans le terminal |
| **Mettre à jour** | `./scripts/update.sh` |
| **Relancer PostgreSQL** | `brew services start postgresql@17` |
| **Relancer Ollama** | `ollama serve &` |
| **Lancer OpenClaw** | `openclaw start` |
| **Voir l'IP du Mac** | `ipconfig getifaddr en0` |
