# Accès distant — Travailler depuis un portable

Le système tourne sur le Mac Studio. Le portable se connecte à distance
pour consulter le dashboard et utiliser OpenClaw.


## Architecture

```
Mac Studio (serveur)                   Portable (client)
┌─────────────────────────┐            ┌──────────────────────┐
│ OpenClaw Gateway :18789 │            │                      │
│ Streamlit       :8501   │◄── réseau ─│  Navigateur → :8501 │
│ Ollama          :11434  │            │  OpenClaw remote     │
│ PostgreSQL      :5432   │            │                      │
└─────────────────────────┘            └──────────────────────┘
```


## Option 1 — Même réseau WiFi (maison/bureau)

Rien à installer sur le portable. Ouvrir le navigateur :

```
http://IP_DU_MAC:8501
```

Pour trouver l'IP du Mac :
```bash
# Sur le Mac Studio
ipconfig getifaddr en0
# → ex: 192.168.1.42
```

Puis sur le portable : `http://192.168.1.42:8501`


## Option 2 — Réseaux différents (en déplacement)

### Méthode A : Tailscale (recommandé, gratuit)

Tailscale crée un réseau privé entre les deux machines.

**Sur le Mac Studio :**
```bash
brew install tailscale
# Suivre les instructions de connexion
```

**Sur le portable :**
- Installer Tailscale : https://tailscale.com/download
- Se connecter avec le même compte

Chaque machine reçoit une IP Tailscale (ex: `100.x.x.x`).
Ouvrir le dashboard : `http://100.x.x.x:8501`

### Méthode B : Tunnel SSH

```bash
# Sur le portable
ssh -L 8501:localhost:8501 -L 18789:localhost:18789 user@adresse_mac

# Puis ouvrir : http://localhost:8501
```


## Accès OpenClaw depuis le portable

OpenClaw a un **mode remote natif**. Le portable se connecte à la
Gateway qui tourne sur le Mac Studio.

### Installation sur le portable (une seule fois)

```bash
npm install -g openclaw
mkdir -p ~/.openclaw
```

Créer `~/.openclaw/openclaw.json` :

```json
{
  "gateway": {
    "mode": "remote",
    "remote": {
      "url": "ws://IP_DU_MAC:18789",
      "token": "votre-token"
    }
  }
}
```

Avec Tailscale, remplacer `IP_DU_MAC` par l'IP Tailscale.
Sans Tailscale, utiliser un tunnel SSH et mettre `127.0.0.1`.

### Utilisation quotidienne

Le Mac et le portable peuvent être utilisés **en même temps**.
Le dashboard Streamlit supporte plusieurs connexions simultanées.
