# Imatra — Logiciel local de préparation des dossiers carte grise

**Imatra** est un logiciel installé localement chez l'agent habilité SIV.
Il prépare, vérifie et pré-remplit les dossiers de cartes grises (VN, VO,
cession) avant soumission au portail SIV — **sans qu'aucune donnée client ne
quitte la machine de l'agent**.

> 💡 Imatra n'est ni un SaaS ni un service en ligne. Il fonctionne hors-ligne
> à 100 % (hormis la vérification cryptographique de la licence et la mise à
> jour optionnelle des règles V-XX/C-XX).

## Pour qui ?

Agents habilités SIV (cabinets, garages, concessions) qui soumettent eux-mêmes
les demandes de carte grise dans le portail officiel et qui ont besoin :

- d'extraire automatiquement les données des documents clients (CNI, permis,
  COC, facture, justificatif de domicile) via PaddleOCR local,
- de croiser ces données contre 38 règles V-XX et 21 règles C-XX,
- d'obtenir un diagnostic VERT / ORANGE / ROUGE en quelques secondes,
- de générer le Cerfa pré-rempli (13749 / 13750 / 15776) en PIL pur,
- de pré-remplir automatiquement le portail SIV via une extension navigateur.

## Architecture

```
api/         FastAPI local (port 8001) — routes dossiers, documents, clients,
             licence, règles, agent, extension SIV
engine/      Moteur métier : OCR PaddleOCR, validations, cross-checks,
             décision, génération Cerfa PIL, RGPD cleanup, licence Ed25519
frontend/    React + Vite + Tailwind — UI agent (dashboard, dossiers, clients,
             paramètres)
extension/   Extension Chrome/Edge (Manifest v3) pour pré-remplir le SIV
storage/     Stockage local chiffré Fernet
data/        Base SQLite, documents, licence (créé au premier lancement)
tests/       253 tests unitaires (pytest)
```

## Installation

Voir [INSTALL.md](INSTALL.md) pour le détail. En résumé :

```bash
# Linux / macOS
bash install.sh

# Windows
install.bat
```

L'installation lance Docker, build l'image (~10 min au premier lancement),
télécharge les modèles PaddleOCR français (~100 Mo) et expose l'interface sur
http://localhost:8001.

## Test E2E

Voir [tests/E2E_SCENARIO.md](tests/E2E_SCENARIO.md) pour le scénario manuel
complet (10 étapes) à exécuter avant chaque release sur une machine vierge.

Tests automatisés : `pytest tests/unit -q` → **253 passants**.

## Sécurité et conformité

- **RGPD** : l'éditeur Imatra ne traite aucune donnée personnelle. L'agent
  est sous-traitant unique de ses clients. Cleanup automatique des données
  sensibles (téléphone, email, prénom) après génération du Cerfa, archivage
  légal du nom 5 ans (R322-9 du Code de la route).
- **Licence** : Ed25519 cryptographique, vérification 100 % locale, mode
  hors-ligne 30 jours.
- **Stockage** : Fernet (AES-128) sur tous les documents.
- **Aucun appel cloud** vers Google, Anthropic, AWS, Twilio, Stripe.

## Licence commerciale

Mode essai gratuit : 30 jours / 10 dossiers. Licence annuelle : 800 € HT/an.

## Version

`2.0.0-local` — voir [CHANGELOG.md](CHANGELOG.md).
