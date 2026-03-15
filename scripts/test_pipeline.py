"""Script de test de la pipeline Phase 2.

Teste la classification, l'OCR et l'extraction sur un document.
Usage : python scripts/test_pipeline.py <chemin_image>
"""

import sys
import json
from pathlib import Path

# Ajouter le répertoire racine au path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


def test_imports():
    """Vérifie que tous les modules s'importent correctement."""
    print("1. Test des imports...")

    from src.ocr.preprocessor import preprocess_for_ocr, preprocess_for_vision
    print("   ✓ preprocessor OK")

    from src.classification.classifier import classify_document
    print("   ✓ classifier OK")

    from src.ocr.engine import extract_text
    print("   ✓ OCR engine OK")

    from src.extraction.carte_grise import CarteGriseExtractor
    from src.extraction.cni import CNIExtractor
    from src.extraction.cession import CessionExtractor
    from src.extraction.justificatif import JustificatifExtractor
    from src.extraction.controle_technique import ControleTechniqueExtractor
    print("   ✓ extracteurs OK")

    print("   Tous les imports OK !\n")


def test_ollama_connection():
    """Vérifie la connexion à Ollama."""
    print("2. Test connexion Ollama...")
    import ollama

    models = ollama.list()
    model_names = [m.model for m in models.models]
    print(f"   Modèles disponibles: {model_names}")

    has_vision = any("qwen2.5vl" in m or "qwen2.5-vl" in m for m in model_names)
    has_text = any("qwen2.5:" in m and "vl" not in m and "coder" not in m for m in model_names)

    print(f"   Vision (qwen2.5vl:7b): {'✓' if has_vision else '✗ MANQUANT'}")
    print(f"   Texte (qwen2.5:7b): {'✓' if has_text else '✗ MANQUANT'}")
    print()


def test_full_pipeline(image_path: str):
    """Teste la pipeline complète sur une image."""
    from src.classification.classifier import classify_document
    from src.ocr.preprocessor import preprocess_for_ocr
    from src.ocr.engine import extract_text, extract_text_from_array
    from src.extraction.carte_grise import CarteGriseExtractor
    from src.extraction.cni import CNIExtractor
    from src.extraction.cession import CessionExtractor
    from src.extraction.justificatif import JustificatifExtractor
    from src.extraction.controle_technique import ControleTechniqueExtractor

    EXTRACTORS = {
        "carte_grise": CarteGriseExtractor(),
        "cni": CNIExtractor(),
        "passeport": CNIExtractor(),
        "certificat_cession": CessionExtractor(),
        "justificatif_domicile": JustificatifExtractor(),
        "controle_technique": ControleTechniqueExtractor(),
    }

    print(f"3. Test pipeline complète sur: {image_path}\n")

    # Étape 1 : Classification
    print("   [ÉTAPE 1] Classification IA (Qwen2.5-VL)...")
    classification = classify_document(image_path)
    print(f"   → Type: {classification['type']} (confiance: {classification['confidence']})")
    print(f"   → Détails: {classification.get('details', '')}\n")

    # Étape 2 : Preprocessing
    print("   [ÉTAPE 2] Preprocessing OpenCV...")
    processed = preprocess_for_ocr(image_path)
    print(f"   → Image traitée: {processed.shape}\n")

    # Étape 3 : OCR
    print("   [ÉTAPE 3] OCR Surya...")
    ocr_result = extract_text_from_array(processed)
    print(f"   → {len(ocr_result['lines'])} lignes extraites")
    print(f"   → Confiance moyenne: {ocr_result['confidence']}")
    print(f"   → Texte brut (100 premiers chars):")
    print(f"     {ocr_result['text'][:100]}...\n")

    # Étape 4 : Extraction structurée
    doc_type = classification["type"]
    if doc_type in EXTRACTORS:
        print(f"   [ÉTAPE 4] Extraction structurée ({doc_type})...")
        extractor = EXTRACTORS[doc_type]
        data = extractor.extract(ocr_result["text"])
        print(f"   → Données extraites:")
        print(json.dumps(data, indent=4, ensure_ascii=False))
    else:
        print(f"   [ÉTAPE 4] Pas d'extracteur pour le type '{doc_type}'")

    print("\n   Pipeline terminée !")


if __name__ == "__main__":
    test_imports()
    test_ollama_connection()

    if len(sys.argv) > 1:
        test_full_pipeline(sys.argv[1])
    else:
        print("Pour tester la pipeline complète, fournir une image :")
        print("  python scripts/test_pipeline.py chemin/vers/image.jpg")
