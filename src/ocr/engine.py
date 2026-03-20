"""Moteur OCR — utilise Ollama vision (qwen2.5vl) pour extraire le texte.

Plus fiable que Surya OCR et deja installe.
"""

from pathlib import Path

import ollama
from PIL import Image

from config.settings import MODEL_VISION


def extract_text(image_path: str | Path, languages: list[str] | None = None) -> dict:
    """Extrait le texte d'une image via le modele vision Ollama."""
    image_path = Path(image_path)
    if not image_path.exists():
        raise FileNotFoundError(f"Image non trouvee: {image_path}")

    # Convertir PDF si necessaire
    if image_path.suffix.lower() == ".pdf":
        image_data = _pdf_to_png(image_path)
    else:
        with open(image_path, "rb") as f:
            image_data = f.read()

    return _run_ocr(image_data)


def extract_text_from_array(image_array, languages: list[str] | None = None) -> dict:
    """Extrait le texte depuis un numpy array (apres preprocessing OpenCV)."""
    import io
    image = Image.fromarray(image_array)
    buf = io.BytesIO()
    image.save(buf, format="PNG")
    return _run_ocr(buf.getvalue())


def _run_ocr(image_data: bytes) -> dict:
    """Execute l'OCR via Ollama vision."""
    response = ollama.chat(
        model=MODEL_VISION,
        messages=[{
            "role": "user",
            "content": (
                "Extrais tout le texte visible de ce document. "
                "Retranscris le texte exactement comme il apparait, "
                "ligne par ligne. Ne commente pas, ne resume pas, "
                "donne uniquement le texte brut."
            ),
            "images": [image_data],
        }],
    )

    text = response["message"]["content"].strip()

    lines = [{"text": line, "confidence": 0.9} for line in text.split("\n") if line.strip()]

    return {
        "text": text,
        "lines": lines,
        "confidence": 0.9,
    }


def _pdf_to_png(pdf_path: Path) -> bytes:
    """Convertit la premiere page d'un PDF en PNG."""
    import io
    import pypdfium2 as pdfium

    pdf = pdfium.PdfDocument(str(pdf_path))
    page = pdf[0]
    bitmap = page.render(scale=2)
    pil_image = bitmap.to_pil()
    pdf.close()

    buf = io.BytesIO()
    pil_image.save(buf, format="PNG")
    return buf.getvalue()
