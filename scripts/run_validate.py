"""Script helper pour le skill OpenClaw carte-grise-validate.
Usage : python scripts/run_validate.py documents.json GENRE
"""
import sys
import json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from src.validation.cross_checker import validate_dossier

if len(sys.argv) < 2:
    print("Usage: python run_validate.py documents.json [GENRE]")
    sys.exit(1)

with open(sys.argv[1], "r") as f:
    docs = json.load(f)

genre = sys.argv[2] if len(sys.argv) > 2 else "VP"
result = validate_dossier(docs, genre_vehicule=genre)
print(json.dumps(result.to_dict(), indent=2, ensure_ascii=False))
