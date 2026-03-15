"""Script helper pour le skill OpenClaw carte-grise-cerfa.
Usage : python scripts/run_cerfa.py demandeur.json vehicule.json taxes.json
"""
import sys
import json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from src.cerfa.filler import fill_cerfa_from_dossier

if len(sys.argv) < 4:
    print("Usage: python run_cerfa.py demandeur.json vehicule.json taxes.json")
    sys.exit(1)

with open(sys.argv[1]) as f:
    demandeur = json.load(f)
with open(sys.argv[2]) as f:
    vehicule = json.load(f)
with open(sys.argv[3]) as f:
    taxes = json.load(f)

path = fill_cerfa_from_dossier(demandeur, vehicule, taxes)
print(json.dumps({"cerfa_path": path, "status": "ok"}, indent=2))
