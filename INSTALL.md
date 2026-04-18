# Installation d'Imatra local

Ce guide vous explique comment installer et lancer **Imatra** sur votre
ordinateur. Le logiciel s'exécute entièrement en local : vos données et celles
de vos clients ne quittent jamais votre machine.

---

## Pré-requis

Vous avez besoin d'un seul logiciel : **Docker Desktop**.

Téléchargez-le gratuitement ici :

- **Windows / macOS** : <https://www.docker.com/products/docker-desktop/>
- **Linux** : `sudo apt install docker.io docker-compose-plugin` (Debian/Ubuntu)
  ou suivez <https://docs.docker.com/engine/install/>

Vérification que Docker fonctionne :

```bash
docker --version
docker compose version
```

Vous devez voir quelque chose comme `Docker version 24.x` et `Docker Compose version v2.x`.

### Configuration recommandée

| Composant | Minimum | Recommandé |
|---|---|---|
| RAM disponible pour Docker | 2 Go | 4 Go |
| Espace disque libre | 5 Go | 10 Go |
| OS | Windows 10/11, macOS 12+, Ubuntu 20.04+ | Idem |

PaddleOCR (le moteur OCR local) télécharge environ 100 Mo de modèles français
au premier démarrage. Cette opération est faite une seule fois.

---

## Installation

### 1. Téléchargez Imatra

Créez un dossier dédié sur votre ordinateur, par exemple :

- **Windows** : `C:\ImatraPro`
- **macOS / Linux** : `~/ImatraPro`

Téléchargez les deux fichiers fournis par Imatra :

- `Dockerfile`
- `docker-compose.yml`

Placez-les dans ce dossier.

### 2. Lancez l'installation

Ouvrez un terminal dans ce dossier puis lancez :

```bash
docker compose up -d
```

Au premier lancement, Docker va :

1. Télécharger l'image de base Python (~150 Mo)
2. Installer PaddleOCR et ses dépendances (~500 Mo)
3. Builder le frontend React
4. Lancer le serveur sur le port 8001

Cette opération prend entre **5 et 15 minutes** selon votre connexion. Les
démarrages suivants sont quasi-instantanés.

### 3. Ouvrez le logiciel

Une fois le démarrage terminé, ouvrez votre navigateur web et allez à :

<http://localhost:8001>

Vous voyez l'interface Imatra. Bienvenue !

---

## Premiers pas

### Configurer votre profil

1. Cliquez sur **Paramètres** dans la barre de gauche
2. Renseignez votre raison sociale, adresse, numéro d'habilitation SIV
3. Cliquez sur **Enregistrer**

### Activer votre licence

1. Toujours dans **Paramètres**, section **Licence**
2. Collez le token de licence reçu par email après votre achat
3. Cliquez sur **Activer**

Si vous n'avez pas encore de licence, vous bénéficiez automatiquement d'un
**essai gratuit de 30 jours** avec **10 dossiers maximum**.

### Traiter votre premier dossier

1. Allez sur le **Tableau de bord**
2. Glissez un email reçu de votre client (`.eml` ou `.msg`) sur la zone bleue
   — ou cliquez pour sélectionner un fichier
3. Le système extrait les pièces jointes, lit les documents et crée un dossier
4. Cliquez sur le dossier pour voir le détail
5. Cliquez sur **Lancer le diagnostic** puis sur **Générer le Cerfa** quand
   tout est vert

---

## Commandes utiles

### Voir les logs

```bash
docker compose logs -f imatra
```

### Arrêter le logiciel

```bash
docker compose stop
```

### Redémarrer

```bash
docker compose restart
```

### Mettre à jour vers la dernière version

```bash
docker compose pull
docker compose up -d
```

### Sauvegarder vos données

Toutes vos données (BDD SQLite, documents chiffrés, licence, règles à jour)
sont dans le dossier `data/` créé à côté de `docker-compose.yml`.

Pour sauvegarder, copiez ce dossier sur un disque externe, un NAS, ou un
service de sauvegarde de votre choix.

```bash
# Exemple avec tar
tar -czf imatra-backup-$(date +%Y%m%d).tar.gz data/
```

### Restaurer une sauvegarde

```bash
# Arrêter le logiciel
docker compose down

# Restaurer le dossier
tar -xzf imatra-backup-20260415.tar.gz

# Relancer
docker compose up -d
```

---

## Résolution de problèmes

### Le port 8001 est déjà utilisé

Modifiez `docker-compose.yml` pour exposer un autre port :

```yaml
ports:
  - "8002:8001"   # Hôte:Container — accédez ensuite via localhost:8002
```

### Docker n'arrive pas à démarrer le container

Vérifiez que Docker Desktop est bien lancé :

- **Windows / macOS** : ouvrez l'application Docker Desktop
- **Linux** : `sudo systemctl status docker`

Vérifiez les logs :

```bash
docker compose logs imatra
```

### PaddleOCR met du temps à démarrer

C'est normal au premier lancement (téléchargement des modèles français).
Comptez 1 à 2 minutes la première fois. Les démarrages suivants prennent
moins de 10 secondes.

### Comment vérifier que tout fonctionne ?

```bash
curl http://localhost:8001/health
```

Doit retourner :

```json
{"status": "ok", "version": "2.0.0-local", "mode": "local", "ocr_provider": "paddle"}
```

---

## Sécurité et confidentialité

- **Aucune donnée client ne quitte votre ordinateur**, sauf la vérification
  optionnelle de licence et le téléchargement automatique des règles V-XX/C-XX
  à jour (qui ne contient aucune donnée personnelle).
- Tous les documents stockés sur le disque sont **chiffrés en AES-128** via
  Fernet. La clé de chiffrement est générée au premier démarrage et reste
  sur votre machine (`data/.encryption_key`, lecture restreinte).
- Imatra **n'envoie aucun email, SMS, ni notification** à un service
  tiers. Les emails de relance générés sont du texte que vous copiez-collez
  dans votre client email habituel (Gmail, Outlook, Thunderbird).
- Vous êtes seul responsable de la conformité des dossiers que vous soumettez
  au SIV. Imatra est un outil d'aide à la décision.

---

## Support

- Consultez la documentation : <https://imatra.fr/docs>
- Email : <support@imatra.fr>
- En cas de bug, joignez les logs (`docker compose logs imatra > logs.txt`)
