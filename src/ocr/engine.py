"""Moteur OCR — Surya wrapper.

Extrait le texte brut d'un document scanné ou photographié.
Utilise Surya OCR avec accélération MPS (Apple Silicon).
"""

from pathlib import Path

from PIL import Image
from surya.recognition import RecognitionPredictor
from surya.detection import DetectionPredictor


# Chargement lazy des modèles (lourds en RAM)
_recognition_predictor = None
_detection_predictor = None


def _get_predictors():
    """Charge les modèles Surya une seule fois (lazy loading)."""
    global _recognition_predictor, _detection_predictor
    if _recognition_predictor is None:
        _recognition_predictor = RecognitionPredictor()
        _detection_predictor = DetectionPredictor()
    return _recognition_predictor, _detection_predictor


def extract_text(image_path: str | Path, languages: list[str] | None = None) -> dict:
    """Extrait le texte d'une image via Surya OCR.

    Args:
        image_path: Chemin vers l'image.
        languages: Liste des langues (défaut: ["fr"]).

    Returns:
        Dict avec :
        - text: texte brut complet
        - lines: liste de lignes avec texte et confiance
        - confidence: score de confiance moyen
    """
    if languages is None:
        languages = ["fr"]

    image_path = Path(image_path)
    if not image_path.exists():
        raise FileNotFoundError(f"Image non trouvée: {image_path}")

    image = Image.open(image_path)
    recognition_predictor, detection_predictor = _get_predictors()

    predictions = recognition_predictor([image], [languages], detection_predictor)

    if not predictions or not predictions[0].text_lines:
        return {"text": "", "lines": [], "confidence": 0.0}

    result = predictions[0]
    lines = []
    total_confidence = 0.0

    for line in result.text_lines:
        lines.append({
            "text": line.text,
            "confidence": line.confidence,
        })
        total_confidence += line.confidence

    full_text = "\n".join(line.text for line in result.text_lines)
    avg_confidence = total_confidence / len(lines) if lines else 0.0

    return {
        "text": full_text,
        "lines": lines,
        "confidence": round(avg_confidence, 3),
    }


def extract_text_from_array(image_array, languages: list[str] | None = None) -> dict:
    """Extrait le texte depuis un numpy array (après preprocessing OpenCV).

    Args:
        image_array: Image numpy array (BGR ou grayscale).
        languages: Liste des langues (défaut: ["fr"]).

    Returns:
        Même format que extract_text().
    """
    if languages is None:
        languages = ["fr"]

    image = Image.fromarray(image_array)
    recognition_predictor, detection_predictor = _get_predictors()

    predictions = recognition_predictor([image], [languages], detection_predictor)

    if not predictions or not predictions[0].text_lines:
        return {"text": "", "lines": [], "confidence": 0.0}

    result = predictions[0]
    lines = []
    total_confidence = 0.0

    for line in result.text_lines:
        lines.append({
            "text": line.text,
            "confidence": line.confidence,
        })
        total_confidence += line.confidence

    full_text = "\n".join(line.text for line in result.text_lines)
    avg_confidence = total_confidence / len(lines) if lines else 0.0

    return {
        "text": full_text,
        "lines": lines,
        "confidence": round(avg_confidence, 3),
    }
