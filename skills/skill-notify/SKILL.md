---
name: carte-grise-notify
description: Envoie un email à la personne habilitée (accusé réception, relance documents, envoi CERFA).
user-invocable: true
metadata: {"openclaw": {"requires": {"bins": ["python3"], "env": ["IMAP_USER", "IMAP_PASSWORD"]}}}
---

# Notification par email

Types : accuse_reception, relance_documents, cerfa, erreur

```bash
cd $PROJECT_DIR && source venv/bin/activate && python3 scripts/run_notify.py TYPE TO REFERENCE [ARGS...]
```

IMPORTANT : Ne jamais envoyer le CERFA à l'ANTS.
On l'envoie uniquement à la personne habilitée SIV.
