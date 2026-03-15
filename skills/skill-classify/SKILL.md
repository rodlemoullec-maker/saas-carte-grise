---
name: carte-grise-classify
description: Classifie un document image (carte grise, CNI, cession, justificatif, CT, assurance). Donne le chemin d'une image en paramètre.
user-invocable: true
metadata: {"openclaw": {"requires": {"bins": ["python3"]}}}
---

# Classification de document carte grise

Quand on te demande de classifier un document, exécute :

```bash
cd $PROJECT_DIR && source venv/bin/activate && python3 -c "
import sys; sys.path.insert(0, '.')
from src.classification.classifier import classify_document
import json
result = classify_document(sys.argv[1])
print(json.dumps(result, indent=2, ensure_ascii=False))
" "$ARGUMENTS"
```

Le résultat est un JSON avec `type`, `confidence` et `details`.
