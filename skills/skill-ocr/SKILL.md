---
name: carte-grise-ocr
description: Extrait le texte brut d'un document image par OCR (Surya). Donne le chemin d'une image en paramètre.
user-invocable: true
metadata: {"openclaw": {"requires": {"bins": ["python3"]}}}
---

# OCR document

Quand on te demande d'extraire le texte d'un document, exécute :

```bash
cd $PROJECT_DIR && source venv/bin/activate && python3 -c "
import sys; sys.path.insert(0, '.')
from src.ocr.preprocessor import preprocess_for_ocr
from src.ocr.engine import extract_text_from_array
import json
processed = preprocess_for_ocr(sys.argv[1])
result = extract_text_from_array(processed)
print(json.dumps({'text': result['text'], 'confidence': result['confidence'], 'nb_lines': len(result['lines'])}, indent=2, ensure_ascii=False))
" "$ARGUMENTS"
```
