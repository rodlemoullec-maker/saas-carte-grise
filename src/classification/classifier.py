"""Classification de documents par IA vision.

Utilise Qwen2.5-VL via Ollama pour identifier le type de document
parmi : carte_grise, cni, passeport, justificatif_domicile,
certificat_cession, controle_technique, attestation_assurance, facture_vente.
"""

import base64
import json
from pathlib import Path

import ollama

from config.settings import MODEL_VISION

CLASSIFICATION_PROMPT = """Tu es un expert en documents administratifs français liés à l'automobile.
Classifie ce document parmi les types suivants :

- carte_grise : Certificat d'immatriculation (document gris/bleu avec des champs A, B, C.1, D.1, E, J.1, P.1, etc.)
- cni : Carte nationale d'identité française (recto ou verso)
- passeport : Passeport français ou étranger
- permis_conduire : Permis de conduire français (format carte rose ou format carte à puce, avec catégories AM, A1, A2, A, B, etc.)
- justificatif_domicile : Facture EDF, eau, téléphone, internet, avis d'impôt, quittance de loyer
- certificat_cession : CERFA 15776, certificat de cession d'un véhicule (formulaire avec vendeur/acheteur)
- controle_technique : Procès-verbal de contrôle technique (avec résultat favorable/défavorable)
- certificat_conformite : Certificat de conformité européen (COC), document technique du constructeur avec rubriques numérotées (0.1, 0.2, 1, 2, 3...)
- attestation_assurance : Attestation d'assurance automobile (carte verte)
- facture_vente : Facture de vente d'un véhicule
- autre : Document non reconnu

Réponds UNIQUEMENT avec un objet JSON valide, sans texte avant ni après :
{"type": "le_type", "confidence": 0.XX, "details": "courte description"}"""


def classify_document(image_path: str | Path) -> dict:
    """Classifie un document image via le modèle vision.

    Args:
        image_path: Chemin vers l'image du document.

    Returns:
        Dict avec les clés : type, confidence, details.
    """
    image_path = Path(image_path)
    if not image_path.exists():
        raise FileNotFoundError(f"Image non trouvée: {image_path}")

    # Encoder l'image en base64
    with open(image_path, "rb") as f:
        image_data = f.read()

    response = ollama.chat(
        model=MODEL_VISION,
        messages=[{
            "role": "user",
            "content": CLASSIFICATION_PROMPT,
            "images": [image_data],
        }],
    )

    raw = response["message"]["content"].strip()

    # Extraire le JSON de la réponse
    try:
        # Chercher le JSON dans la réponse (le modèle peut ajouter du texte)
        start = raw.find("{")
        end = raw.rfind("}") + 1
        if start >= 0 and end > start:
            result = json.loads(raw[start:end])
        else:
            result = {"type": "autre", "confidence": 0.0, "details": f"Réponse non parsable: {raw[:100]}"}
    except json.JSONDecodeError:
        result = {"type": "autre", "confidence": 0.0, "details": f"JSON invalide: {raw[:100]}"}

    # Valider le type
    valid_types = {
        "carte_grise", "cni", "passeport", "permis_conduire",
        "justificatif_domicile", "certificat_cession", "controle_technique",
        "certificat_conformite", "attestation_assurance", "facture_vente",
        "autre",
    }
    if result.get("type") not in valid_types:
        result["type"] = "autre"

    # S'assurer que confidence est un float
    try:
        result["confidence"] = float(result.get("confidence", 0))
    except (ValueError, TypeError):
        result["confidence"] = 0.0

    return result


def classify_documents(image_paths: list[str | Path]) -> list[dict]:
    """Classifie une liste de documents.

    Args:
        image_paths: Liste de chemins vers les images.

    Returns:
        Liste de dicts avec type, confidence, details.
    """
    results = []
    for path in image_paths:
        try:
            result = classify_document(path)
            result["file"] = str(path)
            results.append(result)
        except Exception as e:
            results.append({
                "file": str(path),
                "type": "autre",
                "confidence": 0.0,
                "details": f"Erreur: {e}",
            })
    return results
