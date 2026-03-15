# Guide Opérateur — Utilisation quotidienne

Ce guide décrit comment utiliser le système au quotidien.


## Avant de commencer — Configuration des expéditeurs autorisés

Le système ne traite **QUE** les emails provenant d'adresses que tu as
autorisées. C'est une sécurité pour éviter que n'importe qui déclenche
un traitement.

**Ouvre ce fichier** dans un éditeur de texte :
```
config/expediteurs_autorises.txt
```

**Ajoute les adresses email** des personnes habilitées SIV qui t'envoient
les documents, une par ligne :
```
personne.habilitee@garage-dupont.fr
secretariat@concession-martin.com
```

Sans cette configuration, le système ignorera tous les emails.


## Ce qui se passe quand un email arrive

### Étape par étape :

```
1. Un email arrive dans ta boîte
         │
         ▼
2. Le système vérifie : l'expéditeur est-il autorisé ?
    ├── NON → email ignoré, rien ne se passe
    └── OUI → continue
         │
         ▼
3. Les pièces jointes sont extraites et sauvegardées
         │
         ▼
4. L'IA classifie chaque document :
   "c'est une carte grise", "c'est une CNI", etc.
         │
         ▼
5. L'IA extrait les données de chaque document :
   immatriculation, VIN, nom, adresse, etc.
         │
         ▼
6. Le système recherche le véhicule dans la base
    ├── TROUVÉ → complète avec les données techniques
    └── PAS TROUVÉ → signale les infos manquantes
         │
         ▼
7. Le système vérifie la cohérence entre documents :
   VIN identique ? Noms concordants ? Justificatif récent ?
    ├── TOUT OK → continue
    └── PROBLÈME → prépare un email de relance
         │
         ▼
8. Le système calcule les taxes (selon la région du code postal)
         │
         ▼
9. Le système génère le CERFA 13750 pré-rempli
         │
         ▼
10. Le dossier apparaît dans le dashboard → EN ATTENTE DE TA VALIDATION
```

**IMPORTANT : Aucun email n'est envoyé sans ta validation.**
Le système prépare les emails mais ne les envoie JAMAIS tout seul.
Tu dois valider dans le dashboard avant tout envoi.


## Mode 1 — Tout manuel (recommandé pour commencer)

### Démarrer

```bash
cd ~/Documents/nouveau_projet
source venv/bin/activate
streamlit run dashboard/app.py
```

Dashboard : http://localhost:8501

### Traiter un dossier

1. **"Nouveau traitement"** → importe les documents reçus
2. Le système traite (~30 secondes)
3. **"Dossiers"** → filtre "A valider"
4. Ouvre le dossier :
   - Vérifie les données extraites (corrige si erreur)
   - Vérifie les taxes
   - Télécharge le CERFA PDF
5. En bas du dossier : **emails pré-remplis à copier-coller** :
   - Si tout est bon : copie l'email "Envoi du CERFA" et colle-le dans ton
     logiciel de messagerie, joins le PDF CERFA, et envoie
   - Si documents manquants : copie l'email "Relance" et envoie-le pour
     demander les documents complémentaires
6. Clique "Valider le dossier" puis "Marquer comme envoyé"


## Mode 2 — Semi-automatique (OpenClaw)

### Ce que fait OpenClaw

OpenClaw surveille ta boîte email en continu et traite automatiquement
les dossiers reçus des expéditeurs autorisés. Mais il **n'envoie rien**
sans ta validation.

Concrètement :
- Il détecte les emails → vérifie l'expéditeur → traite le dossier
- Le dossier traité apparaît dans le dashboard avec le statut "A valider"
- **C'est toi qui valides et qui décides d'envoyer** (ou pas)

### Démarrer OpenClaw

```bash
# Terminal 1 : dashboard
cd ~/Documents/nouveau_projet
source venv/bin/activate
streamlit run dashboard/app.py

# Terminal 2 : OpenClaw
openclaw start
```

### Flux quotidien avec OpenClaw

1. OpenClaw tourne en arrière-plan — tu n'as rien à faire
2. Les dossiers traités apparaissent dans le dashboard
3. Tu ouvres le dashboard quand tu veux
4. Tu valides chaque dossier (2-3 minutes)
5. Tu envoies les emails (copier-coller ou manuellement)


## Statuts des dossiers

| Statut | Signification | Ce que tu fais |
|---|---|---|
| `nouveau` | Email reçu, traitement lancé | Rien (le système travaille) |
| `en_cours` | IA en train de traiter | Rien (attends ~30s) |
| `documents_manquants` | Incohérence ou document absent | Copie l'email de relance et envoie-le |
| `pret` | Traitement terminé | Vérifie et valide dans le dashboard |
| `valide` | Tu as validé | Envoie le CERFA par email |
| `envoye` | CERFA envoyé | Dossier terminé |


## Documents reconnus par le système

| Document | Ce que le système en extrait |
|---|---|
| Carte grise | Immatriculation, VIN, marque, cylindrée, puissance, énergie, genre, places, masse |
| CNI / Passeport | Nom, prénom, date naissance, lieu naissance, validité |
| Permis de conduire | Catégories (A1/A2/A/B) — vérification moto |
| Justificatif de domicile | Adresse complète décomposée, date (< 6 mois) |
| Certificat de cession | Vendeur, acheteur, date cession, immatriculation, VIN |
| Contrôle technique | Résultat, date validité |
| Certificat de conformité (COC) | Toutes les specs techniques (pour véhicules absents de la base) |


## Mises à jour

### Automatique

Chaque véhicule traité qui n'est pas dans la base est automatiquement
sauvegardé. La base s'enrichit avec l'usage.

### Manuelle (1x/mois ou en janvier)

```bash
cd ~/Documents/nouveau_projet
source venv/bin/activate
./scripts/update.sh
```

Ce script vérifie les barèmes de taxes et les met à jour si nécessaire.


## En cas de problème

| Problème | Solution |
|---|---|
| Aucun email n'est traité | Vérifie que l'expéditeur est dans `config/expediteurs_autorises.txt` |
| OCR illisible | Demande un meilleur scan/photo |
| IA se trompe sur un champ | Corrige dans le dashboard avant de valider |
| Véhicule non trouvé | Demande le certificat de conformité (COC) |
| CERFA mal aligné | Ajuster les coordonnées dans `src/cerfa/filler.py` |
| OpenClaw ne répond plus | `openclaw restart` |
