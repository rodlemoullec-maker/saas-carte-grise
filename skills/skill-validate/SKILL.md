---
name: carte-grise-validate
description: Vérifie la cohérence entre les documents d'un dossier carte grise (VIN, noms, dates, documents manquants).
user-invocable: true
metadata: {"openclaw": {"requires": {"bins": ["python3"]}}}
---

# Cross-validation documents

```bash
cd $PROJECT_DIR && source venv/bin/activate && python3 scripts/run_validate.py documents.json GENRE
```

Si `is_valid` est False :
- Documents manquants → relancer la personne habilitée
- Incohérences → alerter l'opérateur
