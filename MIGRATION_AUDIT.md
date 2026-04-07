# Audit migration SaaS → Logiciel local

État de référence : commit `7e948e6` (tag `v1.0-saas-final`, branche `legacy/saas`)
Branche de migration : `local/main`

## Fichiers à SUPPRIMER complètement

### Backend — Routes obsolètes (collecte cloud client)

- [ ] `api/routers/public.py` (303 lignes) — URL permanente publique pour création de dossier client-initié
- [ ] `api/routers/client.py` (558 lignes) — Page client mobile via lien SMS
- [ ] `api/routers/scan.py` (172 lignes) — QR code mobile scanner
- [ ] `api/routers/webhooks.py` (79 lignes) — Webhooks Stripe + SIV (plus de paiement par dossier)

### Backend — Notifications cloud

- [ ] `notifications/sms.py` (98 lignes) — Envoi SMS via Twilio
- [ ] `notifications/email.py` (229 lignes) — Envoi email transactionnel (sera remplacé par génération de templates locaux)

### Backend — Paiement par dossier

- [ ] `engine/payment/honoraires.py` (233 lignes) — Stripe pré-autorisation par dossier
- [ ] `engine/payment/taxes_siv.py` (137 lignes) — Gestion taxes SIV (hors périmètre local)
- [ ] Le dossier `engine/payment/` complet

### Backend — OCR cloud

- [ ] `integrations/ocr_providers/google_docai.py` (134 lignes) — Google Document AI
- [ ] `integrations/ocr_providers/azure_form.py` (33 lignes) — Azure Form Recognizer

### Frontend — Pages cloud

- [ ] `frontend/src/PublicClientPage.tsx` (634 lignes) — Page publique client
- [ ] `frontend/src/ClientPage.tsx` (591 lignes) — Page client mobile

### Tests obsolètes

- [ ] `tests/unit/test_sms.py`
- [ ] `tests/unit/test_auth.py` (à voir si JWT cloud reste pertinent)

## Fichiers à MODIFIER

### Backend — Modèles

- [ ] `api/models/professionnel.py` — Supprimer les champs vendeur, agent, slug, mode_facturation
- [ ] `api/models/dossier.py` — Supprimer les champs client_link_token, payment, montant_honoraires, created_by_source
- [ ] `api/main.py` — Retirer les imports et inclusions des routers supprimés

### Backend — Routes

- [ ] `api/routers/professionnel.py` — Simplifier (agent uniquement, retirer setup multi-profils)
- [ ] `api/routers/dossiers.py` — Retirer la logique de paiement par dossier
- [ ] `api/routers/documents.py` — Retirer S3, garder filesystem local
- [ ] `api/routers/decisions.py` — Garder, vérifier les références

### Backend — Configuration

- [ ] `config/settings.py` — Retirer Google, Twilio, Stripe, AWS, JWT cloud, garder local
- [ ] `.env.example` — Reflet de la nouvelle configuration locale
- [ ] `requirements.txt` — Retirer twilio, stripe, google-cloud-documentai, asyncpg, boto3
- [ ] `requirements.txt` — Ajouter paddleocr, aiosqlite, extract-msg

### Backend — Autres

- [ ] `engine/rgpd/cleanup.py` — Adapter pour stockage local
- [ ] `notifications/messages.py` — Réduire à génération de templates locaux uniquement
- [ ] `api/middleware/auth.py` — Simplifier (licence locale au lieu de JWT cloud)
- [ ] `api/middleware/rate_limit.py` — Pas pertinent en local, à supprimer ou désactiver

### Frontend

- [ ] `frontend/src/App.tsx` (2008 lignes !) — Énorme refonte : retirer profils vendeurs, sélecteurs, mode multi-tenant
- [ ] `frontend/src/main.tsx` — Adapter pour routing local
- [ ] `frontend/.env.production` — Retirer URL prod cloud

### Site vitrine

- [ ] `site/index.html` — Refondre en page de vente du logiciel
- [ ] `site/vendeur.html` — Supprimer (vendeur non habilité)
- [ ] `site/agent.html` — Supprimer ou intégrer dans index
- [ ] `site/demo*.html` — Supprimer toutes les démos
- [ ] `site/cgv.html` — Repositionner en CGL (Conditions Générales de Licence)
- [ ] `site/mentions-legales.html` — Mettre à jour
- [ ] `site/confidentialite.html` — Réduire (pas de traitement de données)

## Fichiers à AJOUTER (nouveau)

### Backend

- [ ] `integrations/ocr_providers/paddle_ocr.py` — Provider PaddleOCR
- [ ] `engine/email_parser.py` — Parser d'emails .eml et .msg
- [ ] `engine/dossier_matcher.py` — Détection hybride pour rattachement multi-document
- [ ] `engine/templates/relance/*.txt` — Templates d'emails de relance
- [ ] `notifications/relance_emails.py` — Générateur d'emails de relance
- [ ] `storage/local_encrypted.py` — Stockage local chiffré des documents
- [ ] `api/routers/emails.py` — Endpoint drag & drop emails
- [ ] `api/routers/license.py` — Activation et vérification de licence

### Frontend

- [ ] `frontend/src/components/EmailDropZone.tsx` — Composant drag & drop principal
- [ ] `frontend/src/components/RelanceModal.tsx` — Modal pour les emails de relance
- [ ] `frontend/src/components/DossierMatchPopup.tsx` — Popup de proposition de rattachement
- [ ] `frontend/src/components/LicenseActivation.tsx` — Écran d'activation au premier lancement

### Packaging

- [ ] `Dockerfile` (refonte pour local)
- [ ] `docker-compose.yml` (refonte pour local)
- [ ] `installer/install.sh` — Script d'installation Linux/Mac
- [ ] `installer/install.bat` — Script d'installation Windows
- [ ] `installer/README.md` — Documentation d'installation

### Site vitrine

- [ ] `site/index.html` (refonte) — Page de vente du logiciel
- [ ] `site/telecharger.html` — Page de téléchargement
- [ ] `site/securite.html` — Page sur la sécurité (vos données restent chez vous)
- [ ] `site/cgv.html` (refonte) — Conditions Générales de Licence

### Documentation

- [ ] `docs/installation.md` — Guide d'installation pour l'agent
- [ ] `docs/premier_dossier.md` — Premier dossier en 5 minutes
- [ ] `docs/faq.md` — FAQ technique et juridique

## Dépendances Python

### À retirer de `requirements.txt`

- `google-cloud-documentai` (Google OCR cloud)
- `twilio` (SMS)
- `stripe` (paiement par dossier)
- `boto3` (AWS S3)
- `asyncpg` (PostgreSQL async)
- `azure-ai-formrecognizer` (Azure OCR)

### À ajouter

- `paddleocr` (OCR local)
- `paddlepaddle` (dépendance PaddleOCR)
- `aiosqlite` (SQLite async)
- `extract-msg` (parse Outlook .msg)
- `cryptography` (chiffrement local des documents)

### À garder

- `fastapi`, `uvicorn`, `pydantic`, `sqlalchemy`, `pillow`, `python-multipart`, `anthropic` (Claude pour fallback OCR/extraction si garde, optionnel)

## Variables d'environnement

### À retirer de `.env.example`

- `GOOGLE_PROJECT_ID`, `GOOGLE_LOCATION`, `GOOGLE_DOCAI_PROCESSOR_ID`, `GOOGLE_APPLICATION_CREDENTIALS`
- `STRIPE_SECRET_KEY`, `STRIPE_WEBHOOK_SECRET`
- `TWILIO_ACCOUNT_SID`, `TWILIO_AUTH_TOKEN`, `TWILIO_PHONE_NUMBER`
- `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `AWS_REGION`, `AWS_BUCKET_NAME`
- `SIV_API_URL`, `SIV_API_KEY`, `SIV_HABILITATION_ID`
- `INSEE_API_KEY` (si pertinent — la vérification SIRET reste utile pour la vente)
- `SMTP_*` (notifications email, supprimées)

### À ajouter

- `OCR_PROVIDER=paddle` (par défaut)
- `STORAGE_PATH=./data/documents` (stockage local)
- `STORAGE_ENCRYPTION_KEY=<auto-généré au premier démarrage>`
- `LICENSE_SERVER_URL=https://licenses.autodocpro.fr` (votre serveur de licences)

## Prochaines étapes

Une fois cet audit fait, l'ordre d'exécution est :

1. **Phase 3** (suppression du code obsolète) — vide le projet de tout le SaaS
2. **Phase 2** (migration BDD vers SQLite) — la base devient locale
3. **Phase 1** (PaddleOCR) — l'OCR devient local
4. **Phase 4** (drag & drop emails) — la nouvelle fonction principale
5. **Phase 5** (génération emails de relance) — le complément
6. **Phase 6** (système de licences) — la protection commerciale
7. **Phase 7** (mises à jour des règles) — la maintenance à distance
8. **Phase 8** (frontend local) — adaptation de l'UI
9. **Phase 9** (packaging Docker) — la distribution
10. **Phase 10** (site vitrine) — la vente
11. **Phase 11** (tests E2E) — la validation
12. **Phase 12** (lancement) — la mise en ligne

---

*Dernière mise à jour : début de la migration*
