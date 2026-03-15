---
name: carte-grise-cerfa
description: Génère le CERFA 13750 pré-rempli à partir des données demandeur, véhicule et taxes.
user-invocable: true
metadata: {"openclaw": {"requires": {"bins": ["python3"]}}}
---

# Génération CERFA 13750

```bash
cd $PROJECT_DIR && source venv/bin/activate && python3 scripts/run_cerfa.py demandeur.json vehicule.json taxes.json
```

Le résultat est le chemin du PDF CERFA généré.
Ce fichier doit être envoyé par email à la personne habilitée.
