---
name: carte-grise-vehicle
description: Recherche les caractéristiques techniques d'un véhicule par VIN, immatriculation, CNIT ou marque.
user-invocable: true
metadata: {"openclaw": {"requires": {"bins": ["python3"]}}}
---

# Recherche véhicule

```bash
cd $PROJECT_DIR && source venv/bin/activate && python3 -c "
import sys; sys.path.insert(0, '.')
from src.vehicle.search import search
import json
result = search(vin='$VIN', immatriculation='$IMMAT', cnit='$CNIT', marque='$MARQUE')
print(json.dumps(result, indent=2, ensure_ascii=False, default=str))
"
```
