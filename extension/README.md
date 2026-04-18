# Extension navigateur Imatra — Auto-saisie SIV

Extension Chrome / Edge (Manifest v3) qui pré-remplit les formulaires du
portail SIV (siv.interieur.gouv.fr) ou ANTS (immatriculation.ants.gouv.fr)
à partir d'un dossier préparé dans Imatra (logiciel local installé sur
`http://localhost:8001`).

## Installation (mode développeur)

1. Ouvrir `chrome://extensions` (ou `edge://extensions`)
2. Activer le **mode développeur** (en haut à droite)
3. Cliquer sur **Charger l'extension non empaquetée**
4. Sélectionner le dossier `extension/`

## Utilisation

1. Lancer Imatra local (`docker compose up -d`)
2. Préparer un dossier complet, valider le diagnostic en VERT
3. Ouvrir le portail SIV dans un onglet
4. Cliquer sur l'icône Imatra dans la barre d'extensions
5. Saisir la référence du dossier (`CG-2026-XXXXX`)
6. Cliquer sur **Pré-remplir le formulaire SIV**

L'extension récupère le dossier via `GET http://localhost:8001/siv-payload?ref=…`
et injecte les valeurs dans les champs détectés du formulaire ouvert.

## Calibrage

Les sélecteurs CSS dans `content.js` (`FIELD_MAP`) sont des **placeholders**
basés sur des conventions de nommage probables. Pour une correspondance
parfaite, ouvrir les DevTools sur une vraie session SIV, inspecter les
attributs `name` / `id` des champs, et compléter les listes.

## Sécurité

- L'extension n'envoie **aucune donnée** vers Internet : tout reste entre
  le navigateur, Imatra (localhost) et le portail SIV ouvert par l'agent.
- Les `host_permissions` se limitent à `localhost:8001` + portails SIV/ANTS.
- Aucune télémétrie, aucun service tiers.
