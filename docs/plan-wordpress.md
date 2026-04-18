# Plan d'adaptation — Imatra sur WordPress (Kadence)

## Résumé

Migrer le site commercial Imatra (HTML statique) vers WordPress avec le thème Kadence et le starter template "SaaS & Digital Services". Le backend API et le frontend React restent hébergés séparément (Railway/Render).

---

## Architecture hébergement

| Composant | Hébergeur | Coût |
|---|---|---|
| Site commercial WordPress | Hostinger Premium | 2,99€/mois |
| Backend API (FastAPI) | Railway ou Render | Gratuit → ~5€/mois |
| Frontend App (React) | Railway ou Render | Inclus |
| Base de données (PostgreSQL) | Neon | Gratuit |
| Vidéos démo | YouTube/Vimeo (embed) | Gratuit |

---

## Étape 1 — Installation WordPress (10 min)

1. Hostinger → Sites web → Créer un site → WordPress
2. Choisir un nom de domaine (ou sous-domaine temporaire)
3. Attendre l'installation (~2 min)
4. Accéder à `ton-domaine.com/wp-admin`

## Étape 2 — Thème et template (10 min)

1. Apparence → Thèmes → Ajouter → Chercher "Kadence" → Installer + Activer
2. Extensions → Ajouter → Chercher "Kadence Starter Templates" → Installer + Activer
3. Apparence → Kadence → Starter Templates
4. Chercher "SaaS" ou "Digital Services"
5. À l'import, configurer :
   - Couleur primaire : `#1e40af`
   - Couleur accent : `#059669`
   - Police titre : Outfit
   - Police corps : Inter
6. Importer le template complet

## Étape 3 — Page d'accueil / Vendeur habilité (45 min)

Ouvrir la page d'accueil dans l'éditeur Gutenberg. Remplacer section par section :

### 3.1 Hero

| Élément | Contenu |
|---|---|
| Eyebrow | Pour les vendeurs auto et moto habilités SIV |
| H1 | Le dossier carte grise, automatisé. |
| Paragraphe | Vous déposez vos documents véhicule. Le système lit, extrait, croise et vérifie tout. Il collecte les pièces du client par SMS. Et il génère le Cerfa avec votre cachet et signature. **5 min par dossier. Zéro saisie. Zéro rejet.** |
| Bouton 1 (emerald) | Tester sur mes prochains dossiers → #contact |
| Bouton 2 (outline) | Voir la démo → /demo |
| Visuel droite | Bloc Custom HTML → coller le mockup vendeur habilité (code dans site/index.html, lignes 61-118) |

### 3.2 Chiffres clés

3 blocs Kadence Info Box en ligne :
- **5 min** — par dossier au lieu de 30
- **0** — saisie manuelle
- **100%** — votre client, votre tarif

### 3.3 Le problème

Titre : "Après chaque vente, c'est toujours la même chose"

3 blocs Kadence Info Box (fond gris #f8fafc) :

**Card 1 :**
- Titre : 30 minutes par dossier
- Texte : Remplir le Cerfa, vérifier chaque champ, croiser le VIN entre le COC, la facture et la CG. Du temps que vous ne passez pas à vendre.

**Card 2 :**
- Titre : Des rejets SIV évitables
- Texte : Un 0 à la place d'un O dans le VIN, une CNI expirée, une signature oubliée. Des erreurs simples qui bloquent le dossier. Rejet, correction, renvoi.

**Card 3 :**
- Titre : Les services existants ne vérifient rien
- Texte : Vous uploadez et vous attendez. Un humain relit 12 à 24h plus tard. Et c'est le service qui facture votre client — pas vous.

### 3.4 La solution

Titre : "Déposez les documents. Le système fait le reste."
Sous-titre : "Chaque document est lu, vérifié et croisé dès qu'il est déposé. Quand tout est vert, le Cerfa est prêt."

4 blocs Kadence Info Box (grille 2×2) :

**Card 1 — OCR + IA — zéro saisie** (icône scan-eye, fond bleu clair)
- COC — VIN, marque, modèle, puissance, catégorie, énergie
- Facture — montant, date, identité vendeur
- CG barrée — immatriculation, date de cession, nom acheteur
- CNI / Passeport — nom, prénom, date de naissance, expiration
- Permis — catégories, date d'obtention
- Domicile — nom, adresse, date du document

**Card 2 — Vérification immédiate** (icône shield-check, fond vert clair)
- VIN identique sur le COC, la facture, la CG et la cession
- CNI ou passeport non expiré
- Permis adapté à la puissance du véhicule (A1, A2, B)
- Formation 7h requise pour 125cc en permis B
- Nom CNI cohérent avec le domicile — hébergement détecté
- CG barrée avec date de vente et signatures
- Justificatif de domicile de moins de 6 mois
- *Note italique : Le système vérifie la cohérence et la complétude, pas l'authenticité — c'est votre responsabilité.*

**Card 3 — Collecte client par SMS** (icône smartphone, fond bleu clair)
- Un lien SMS sécurisé est envoyé au client
- Il dépose ses documents depuis son téléphone
- Il est guidé étape par étape (consentement, CPI, upload)
- Le système vérifie chaque document à la seconde
- Vous êtes notifié quand c'est complet
- Si un problème est détecté, le client est invité à corriger

**Card 4 — Cerfa généré automatiquement** (icône file-check, fond vert clair)
- Le Cerfa 13749 (VN) ou 13750 (VO) est pré-rempli
- Votre cachet commercial est apposé automatiquement
- Votre signature est apposée automatiquement
- Vous téléchargez le PDF prêt à soumettre
- Le dossier complet est disponible en ZIP
- VN, VO, moto, voiture, personne morale — le système s'adapte

### 3.5 Comparatif

Bloc Kadence Table :

| | À la main | Services existants | **Imatra** |
|---|---|---|---|
| Vérification | Vous, à l'œil | Un humain, 12-24h | **Automatique, à la seconde** |
| Erreur détectée | Au rejet SIV | Relance messagerie | **Au dépôt, immédiatement** |
| Saisie Cerfa | Manuelle | Formulaire | **Extraite des documents** |
| Temps | 30 min | 10 min + attente | **5 min** |
| Qui fixe le prix | Vous | Le service | **Vous** |
| Coût | Votre temps | Commission | **12-14€ par dossier** |

Colonne Imatra : fond vert clair, texte gras.

### 3.6 Mockup mobile client

Titre : "Ce que voit votre client sur son téléphone"
Sous-titre : "Il reçoit un SMS, ouvre le lien, et dépose ses documents en 3 minutes."

Bloc Custom HTML → coller le code du mockup iPhone (code dans site/index.html, lignes 247-278).

Sous le mockup : "Le client ne voit jamais Imatra — seulement le nom de votre commerce."

### 3.7 Tarifs

Titre : "Prix fixe. Vous facturez ce que vous voulez."
Sous-titre : "Pas d'abonnement — vous payez uniquement par dossier traité."

Bloc Kadence Pricing Table (2 colonnes) :

**Moto — 12€ HT / dossier**
- OCR + IA + vérification automatique
- Collecte client par SMS
- Cerfa généré avec cachet et signature
- URL permanente incluse
- Bouton : Commencer → #contact

**Voiture — 14€ HT / dossier** ★ Le plus courant
- Même features
- Bouton : Commencer → #contact
- Badge "Le plus courant" en haut

Note : "5 premiers dossiers sans avance de frais. Facturés uniquement si vous continuez. Si vous arrêtez, rien n'est dû."

### 3.8 FAQ

Bloc Kadence Accordion (5 items) :

1. **Je dois envoyer un lien au client ou je peux tout déposer moi-même ?**
   Les deux. Si vous avez tous les documents du client, déposez tout — le système vérifie immédiatement. S'il manque des pièces, envoyez un lien SMS au client : il dépose depuis son téléphone et vous êtes notifié quand c'est complet.

2. **Le client voit-il Imatra ?**
   Non. Le client voit votre nom de commerce. Vous restez son unique interlocuteur.

3. **Je ne suis pas habilité SIV — je peux utiliser Imatra ?**
   Oui. Le système prépare votre dossier et vous le transmettez à votre agent habilité. [En savoir plus →](/vendeur)

4. **Je suis agent habilité, pas vendeur — ça marche aussi ?**
   Oui. Le système s'adapte : vos clients déposent leurs docs via votre lien permanent, vous vérifiez et soumettez. [En savoir plus →](/agent)

5. **Je suis engagé si je m'inscris ?**
   Non. 5 dossiers pour tester, sans rien avancer. Si vous continuez, vous réglez. Si vous arrêtez, vous ne devez rien.

### 3.9 Formulaire contact

Titre : "Testez sur vos prochains dossiers"
Sous-titre : "Inscription automatique — votre espace est prêt en quelques minutes"

Champs (Kadence Form ou WPForms) :
- Nom * (texte)
- Prénom * (texte)
- Email * (email)
- Téléphone (tél)
- Nom de votre commerce ou structure (texte)
- Votre profil * (select) : Vendeur habilité SIV [sélectionné] / Vendeur non habilité / Agent habilité SIV
- Volume mensuel * (select) : Sélectionnez / 1 à 5 / 5 à 20 / 20 à 50 / Plus de 50
- Bouton : Commencer mon essai (emerald)

Réassurance sous le bouton (3 textes en ligne) :
- Sans carte bancaire
- Prêt en quelques minutes
- Aucun engagement

### 3.10 Sections à SUPPRIMER du template

- Testimonials / logos clients
- Our Team
- Blog / Articles
- Newsletter
- Toute image stock générique

---

## Étape 4 — Page vendeur non habilité (30 min)

1. Dupliquer la page d'accueil (plugin Duplicate Page)
2. Renommer "Vendeur non habilité" — slug : `vendeur`
3. Modifier :

### Différences avec la page d'accueil

| Section | Contenu vendeur non habilité |
|---|---|
| Eyebrow | Pour les vendeurs auto et moto sans habilitation SIV |
| H1 | Vous vendez, votre agent soumet. |
| Paragraphe | Vous préparez le dossier avec Imatra. Le système vérifie tout. Vous transmettez le dossier complet à votre agent habilité pour la soumission au SIV. Même qualité, pas d'habilitation nécessaire. |
| Mockup hero | Mockup VN moto 125cc + formation 7h + double mandat (code dans site/index-old.html, lignes 296-331) |
| Problème card 1 | **Vous n'êtes pas habilité SIV** — Vous ne pouvez pas soumettre au SIV vous-même |
| Problème card 2 | **Votre agent fait le travail à l'aveugle** — Vous lui envoyez les docs par email, il revérifie tout |
| Problème card 3 | **Vous perdez le contrôle** — Pas de visibilité sur l'avancement, le client attend |
| Solution card 1 | **Vous préparez, le système vérifie** (icône scan-eye) — puces : VIN, marque, modèle... / Cohérence VIN... / Permis adapté... / Erreurs signalées... |
| Solution card 2 | **Le client dépose par SMS** (icône smartphone) — puces : CNI recto+verso... / Permis... / Domicile... / Signature mandats... / Guidé étape par étape... |
| Solution card 3 | **Le double mandat est géré** (icône file-signature) — puces : Mandat client→vendeur... / Mandat client→agent... / Pré-remplis... / Signés numériquement... / Rien à imprimer... |
| Solution card 4 | **Vous transmettez le ZIP** (icône archive) — puces : Cerfa pré-rempli... / Mandats signés... / Documents vérifiés... / ZIP téléchargeable... / Agent n'a plus qu'à soumettre... |
| Section ajoutée | **Le double mandat, simplifié** — La FAQ DSR prévoit qu'un vendeur non habilité mandaté par ses clients peut solliciter un professionnel habilité SIV. Deux mandats Cerfa 13757 : (1) client mandate le vendeur, (2) client mandate l'agent. Imatra les génère et les fait signer. |
| Comparatif | SUPPRIMER |
| Mockup mobile | SUPPRIMER |
| FAQ Q1 | **Comment mon agent reçoit le dossier ?** — ZIP téléchargeable (email, messagerie, clé USB) |
| FAQ Q2 | **Mon agent doit-il s'inscrire ?** — Non, il reçoit le ZIP prêt |
| FAQ Q3 | **Qui est responsable ?** — L'agent habilité soumet sous sa responsabilité |
| FAQ Q4 | **C'est légal ?** — Oui, FAQ DSR, double mandat Cerfa 13757 |
| FAQ Q5 | **Je suis engagé ?** — Non, 5 dossiers essai |
| Formulaire profil | Pré-sélectionné "Vendeur non habilité" |

---

## Étape 5 — Page agent habilité (30 min)

1. Dupliquer la page d'accueil
2. Renommer "Agent habilité SIV" — slug : `agent`
3. Modifier :

### Différences avec la page d'accueil

| Section | Contenu agent habilité |
|---|---|
| Eyebrow | Pour les agents habilités SIV |
| H1 | Vos clients déposent, vous soumettez. |
| Paragraphe | Vos clients viennent chez vous pour leur carte grise. Avec Imatra, ils déposent leurs documents via votre URL permanente imatra.fr/votre-commerce. Le système vérifie tout. Vous téléchargez le Cerfa et soumettez au SIV. |
| Mockup hero | Mockup VO entre particuliers via URL permanente (code dans site/index-old.html, lignes 334-395) — badge "Client public", tous docs "dép. client", hébergement détecté |
| Problème card 1 | **Collecter par email, c'est lent** — le client envoie les docs un par un, mauvais format, allers-retours |
| Problème card 2 | **Vérifier à l'œil, c'est risqué** — CNI expirée, nom divergent, vous le voyez après soumission |
| Problème card 3 | **Pas de visibilité pour le client** — le client ne sait pas où en est son dossier |
| Solution card 1 | **URL permanente** (icône globe) — puces : CG barrée et cession VO... / CNI recto+verso... / Permis... / Domicile... / Client voit votre nom... / Notifié quand complet... |
| Solution card 2 | **Vérification automatique** (icône shield-check) — puces : CNI non expirée... / Nom cohérent... / Hébergement détecté... / Cession remplie... / Domicile < 6 mois... / Chaque problème expliqué... |
| Solution card 3 | **Lien SMS pour les corrections** (icône smartphone) — puces : Envoyez lien en un clic... / Client corrige... / Re-vérifie auto... / Notifié quand corrigé... / Pas besoin de se déplacer... |
| Solution card 4 | **Cerfa prêt** (icône file-check) — puces : Cerfa 13750 pré-rempli... / Cachet apposé... / Signature apposée... / PDF téléchargeable... / ZIP complet... |
| Section ajoutée | **URL permanente — imatra.fr/votre-commerce** — Générée automatiquement à l'inscription. Mettez-la partout : site web, fiche Google, réseaux sociaux, vitrine QR code. Le client dépose ses docs + docs véhicule. SEO : chaque page pro indexable. |
| Comparatif | SUPPRIMER |
| Mockup mobile | SUPPRIMER |
| FAQ Q1 | **Le client dépose aussi les docs véhicule ?** — Oui, pour un agent le client apporte tout (CG barrée, cession déjà signée) |
| FAQ Q2 | **La cession est gérée par le système ?** — Non, le client arrive avec sa cession déjà signée. Le système la vérifie. |
| FAQ Q3 | **L'URL permanente est gratuite ?** — Oui, incluse |
| FAQ Q4 | **Mon client voit Imatra ?** — Non, seulement votre nom de commerce |
| FAQ Q5 | **Je suis engagé ?** — Non, 5 dossiers essai |
| Formulaire profil | Pré-sélectionné "Agent habilité" |

---

## Étape 6 — Navigation WordPress

Apparence → Personnaliser → Menus :

```
Vendeur habilité        → / (accueil)
Vendeur non habilité    → /vendeur/
Agent SIV               → /agent/
Comment ça marche       → /comment-ca-marche/
Tarifs                  → /#tarifs (ancre)
FAQ                     → /#faq (ancre)
[Bouton CTA] Essai sans engagement → /#contact (ancre)
```

---

## Étape 7 — Pages légales (20 min)

Créer 4 pages WordPress standard (pas de template, juste du texte) :

1. **Comment ça marche** (`/comment-ca-marche/`) → copier le contenu de `site/comment-ca-marche.html`
2. **CGV** (`/cgv/`) → copier le contenu de `site/cgv.html`
3. **Mentions légales** (`/mentions-legales/`) → copier le contenu de `site/mentions-legales.html`
4. **Confidentialité** (`/confidentialite/`) → copier le contenu de `site/confidentialite.html`

---

## Étape 8 — Pages démo (15 min)

Créer 3 pages WordPress :

1. **Démo vendeur habilité** (`/demo/`) → bloc Custom HTML → coller le contenu de `site/demo.html` (entre `<body>` et `</body>`)
2. **Démo vendeur non habilité** (`/demo-vendeur/`) → bloc Custom HTML → coller `site/demo-vendeur.html`
3. **Démo agent** (`/demo-agent/`) → bloc Custom HTML → coller `site/demo-agent.html`

---

## Étape 9 — CSS custom (10 min)

Apparence → Personnaliser → CSS additionnel :

Coller les styles suivants depuis `site/assets/css/style.css` :
- Styles des mockups d'interface (hero-visual, demo-*)
- Animations fade-in
- Styles du comparatif (barre verte latérale)
- Styles du pricing highlight
- Styles de réassurance formulaire
- Styles feat-card-icon

---

## Étape 10 — Plugins à installer

| Plugin | Rôle | Gratuit |
|---|---|---|
| Kadence Blocks | Blocs avancés (info box, pricing, accordion, tabs) | Oui |
| Kadence Starter Templates | Import du template | Oui |
| WPForms Lite | Formulaire de contact | Oui |
| Duplicate Page | Dupliquer les pages | Oui |
| Yoast SEO | SEO, sitemap, meta OG | Oui |
| Plausible Analytics | Analytics RGPD-friendly | Oui (self-hosted) ou 9€/mois |

---

## Étape 11 — Optimisation conversion

1. Header sticky + transparent sur hero
2. Bouton CTA nav en emerald (#059669)
3. Footer 4 colonnes (Profils / Légal / Contact / Logo)
4. Formulaire connecté à email (WPForms + SMTP)
5. Favicon SVG uploadé
6. Meta OG via Yoast sur chaque page
7. robots.txt + sitemap auto via Yoast
8. Test mobile sur les 3 pages profils

---

## Étape 12 — Vidéos de démo (plus tard)

Quand le produit tournera en vrai :
1. Enregistrer 3 vidéos de démo (1 par profil, 60-90 secondes)
2. Uploader sur YouTube (non listé)
3. Embed dans le hero de chaque page (remplace le mockup HTML)
4. Ajouter un poster (thumbnail) pour le chargement

---

## Checklist finale

- [ ] Kadence installé et template importé
- [ ] Palette navy/emerald/primary appliquée
- [ ] Typo Outfit (titres) + Inter (corps)
- [ ] Page accueil = vendeur habilité
- [ ] Page vendeur non habilité créée et personnalisée
- [ ] Page agent habilité créée et personnalisée
- [ ] Mockups d'interface intégrés (Custom HTML)
- [ ] Navigation cohérente sur toutes les pages
- [ ] Formulaire fonctionnel avec sélecteur de profil
- [ ] Pages légales créées (CGV, mentions, confidentialité, comment ça marche)
- [ ] Pages démo créées
- [ ] CSS custom ajouté
- [ ] Yoast SEO configuré (meta, sitemap, OG)
- [ ] Favicon uploadé
- [ ] Mobile vérifié
- [ ] Formulaire testé (réception email)

---

## Fichiers sources (contenu à copier-coller)

Tous les fichiers sont dans `/Users/rodolph/Documents/nouveau_projet/site/` :

| Fichier | Utilisation |
|---|---|
| `index.html` | Contenu page accueil (vendeur habilité) |
| `vendeur.html` | Contenu page vendeur non habilité |
| `agent.html` | Contenu page agent habilité |
| `comment-ca-marche.html` | Page comment ça marche |
| `cgv.html` | Conditions générales de vente |
| `mentions-legales.html` | Mentions légales |
| `confidentialite.html` | Politique de confidentialité |
| `demo.html` | Démo vendeur habilité |
| `demo-vendeur.html` | Démo vendeur non habilité |
| `demo-agent.html` | Démo agent habilité |
| `assets/css/style.css` | CSS custom à extraire |
| `favicon.svg` | Favicon |
