"""Script helper pour le skill OpenClaw carte-grise-extract.
Usage : python scripts/run_extract.py TYPE fichier_ocr.txt
"""
import sys
import json
import importlib
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

EXTRACTORS = {
    "carte_grise": "src.extraction.carte_grise:CarteGriseExtractor",
    "cni": "src.extraction.cni:CNIExtractor",
    "passeport": "src.extraction.cni:CNIExtractor",
    "certificat_cession": "src.extraction.cession:CessionExtractor",
    "justificatif_domicile": "src.extraction.justificatif:JustificatifExtractor",
    "controle_technique": "src.extraction.controle_technique:ControleTechniqueExtractor",
    "certificat_conformite": "src.extraction.conformite:ConformiteExtractor",
    "permis_conduire": "src.extraction.permis:PermisExtractor",
}

if len(sys.argv) < 3:
    print("Usage: python run_extract.py TYPE fichier_ocr.txt")
    sys.exit(1)

doc_type = sys.argv[1]
ocr_file = sys.argv[2]

if doc_type not in EXTRACTORS:
    print(f"Type inconnu: {doc_type}. Types: {list(EXTRACTORS.keys())}")
    sys.exit(1)

with open(ocr_file, "r") as f:
    ocr_text = f.read()

module_path, class_name = EXTRACTORS[doc_type].rsplit(":", 1)
module = importlib.import_module(module_path)
extractor = getattr(module, class_name)()
result = extractor.extract(ocr_text)
print(json.dumps(result, indent=2, ensure_ascii=False))
