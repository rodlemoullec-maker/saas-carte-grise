# Changelog

## 2.0.0-local — 2026-04-07

Version initiale du logiciel **Imatra local** (anciennement AutoDoc Pro SaaS).
Migration complète depuis l'architecture cloud vers une installation locale
chez l'agent habilité SIV.

### Ajouté

- **Moteur OCR local** PaddleOCR (remplace Google Document AI)
- **Base SQLite** locale (remplace PostgreSQL Neon)
- **Stockage chiffré Fernet** (remplace S3)
- **Licence cryptographique Ed25519** avec mode hors-ligne 30 jours
- **Mises à jour des règles** V-XX/C-XX par bundle signé
- **Drag & drop d'emails** (.eml, .msg) avec extraction automatique des PJ
- **Génération Cerfa 100 % PIL** (13749 VN, 13750 VO, 15776 cession)
- **Diagnostic tri-couleur** VERT / ORANGE / ROUGE binaire
- **Email de relance** copiable presse-papier (28 templates)
- **Cleanup RGPD** automatique après génération Cerfa
- **Base clients récurrents** (PHYSIQUE / MORALE) avec recherche
- **Export ZIP enrichi** avec `manifest.xml` et `SHA256SUMS`
- **Rappel UI archivage** légal 5 ans après Cerfa
- **Extension navigateur SIV** (Chrome/Edge Manifest v3) pour auto-saisie
- **Packaging Docker** (multi-stage build, healthcheck, install.sh/bat)
- **253 tests unitaires** (pytest)

### Supprimé

- Toute dépendance cloud (Google, AWS, Twilio, Stripe, Anthropic)
- Système multi-tenant SaaS
- Liens SMS clients, signature OTP, mandat 13757
- Playwright pour la génération Cerfa
- Pages publiques `/public/{slug}`, webhooks Stripe/SIV

### Renommé

- **AutoDoc Pro → Imatra** (avril 2026, conflit avec AUTODOC GmbH)
