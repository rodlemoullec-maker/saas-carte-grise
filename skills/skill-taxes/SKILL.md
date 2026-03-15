---
name: carte-grise-taxes
description: Calcule les taxes carte grise (Y1 régionale, Y3 formation, Y4 malus CO2, Y5 malus masse, Y6 fixe).
user-invocable: true
metadata: {"openclaw": {"requires": {"bins": ["python3"]}}}
---

# Calcul taxes

```bash
cd $PROJECT_DIR && source venv/bin/activate && python3 -c "
import sys; sys.path.insert(0, '.')
from src.taxes.calculator import calculer_taxes
import json
result = calculer_taxes(puissance_fiscale=$PF, region='$REGION', energie='$ENERGIE', co2=$CO2, masse=$MASSE, genre='$GENRE', est_neuf=False)
print(json.dumps(result, indent=2, ensure_ascii=False))
"
```
