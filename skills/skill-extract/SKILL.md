---
name: carte-grise-extract
description: Extrait les données structurées (JSON) depuis du texte OCR selon le type de document (carte_grise, cni, cession, justificatif, controle_technique).
user-invocable: true
metadata: {"openclaw": {"requires": {"bins": ["python3"]}}}
---

# Extraction structurée

Crée un fichier temporaire avec le texte OCR, puis exécute le script.
Remplace TYPE par le type de document et le contenu du fichier par le texte OCR.

```bash
cd $PROJECT_DIR && source venv/bin/activate && python3 scripts/run_extract.py TYPE /chemin/vers/ocr_text.txt
```
