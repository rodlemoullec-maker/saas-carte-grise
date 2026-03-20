"""Prétraitement image avant OCR.

Améliore la qualité des photos/scans de documents pour maximiser
la précision de l'OCR (Surya). Particulièrement utile pour les
photos prises au smartphone.
"""

import cv2
import numpy as np
from pathlib import Path


def _pdf_to_cv2(pdf_path: str | Path) -> np.ndarray:
    """Convertit la premiere page d'un PDF en image OpenCV."""
    import pypdfium2 as pdfium

    pdf = pdfium.PdfDocument(str(pdf_path))
    page = pdf[0]
    bitmap = page.render(scale=2)
    pil_image = bitmap.to_pil()
    pdf.close()

    img_array = np.array(pil_image)
    # Convertir RGB -> BGR pour OpenCV
    if len(img_array.shape) == 3 and img_array.shape[2] >= 3:
        img_array = cv2.cvtColor(img_array, cv2.COLOR_RGB2BGR)
    return img_array


def preprocess_image(image_path: str | Path, output_path: str | Path | None = None) -> np.ndarray:
    """Prétraite une image ou PDF de document pour l'OCR.

    Args:
        image_path: Chemin vers l'image ou PDF source.
        output_path: Si fourni, sauvegarde l'image prétraitée.

    Returns:
        Image prétraitée (numpy array).
    """
    image_path = Path(image_path)

    # Convertir PDF en image si necessaire
    if image_path.suffix.lower() == ".pdf":
        img = _pdf_to_cv2(image_path)
    else:
        img = cv2.imread(str(image_path))

    if img is None:
        raise FileNotFoundError(f"Impossible de lire l'image: {image_path}")

    # 1. Conversion en niveaux de gris
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

    # 2. Redimensionnement si l'image est trop petite (min 1500px de large)
    h, w = gray.shape
    if w < 1500:
        scale = 1500 / w
        gray = cv2.resize(gray, None, fx=scale, fy=scale, interpolation=cv2.INTER_CUBIC)

    # 3. Débruitage
    denoised = cv2.fastNlMeansDenoising(gray, h=10, templateWindowSize=7, searchWindowSize=21)

    # 4. Amélioration du contraste (CLAHE)
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    enhanced = clahe.apply(denoised)

    # 5. Binarisation adaptative (texte noir sur fond blanc)
    binary = cv2.adaptiveThreshold(
        enhanced, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 21, 10
    )

    if output_path:
        cv2.imwrite(str(output_path), binary)

    return binary


def deskew(image: np.ndarray) -> np.ndarray:
    """Redresse une image légèrement inclinée.

    Détecte l'angle d'inclinaison via les lignes de texte
    et applique une rotation corrective.
    """
    coords = np.column_stack(np.where(image < 128))
    if len(coords) < 100:
        return image

    angle = cv2.minAreaRect(coords)[-1]

    if angle < -45:
        angle = -(90 + angle)
    else:
        angle = -angle

    # Ne corriger que les petites inclinaisons (< 15°)
    if abs(angle) > 15 or abs(angle) < 0.5:
        return image

    h, w = image.shape[:2]
    center = (w // 2, h // 2)
    matrix = cv2.getRotationMatrix2D(center, angle, 1.0)
    rotated = cv2.warpAffine(
        image, matrix, (w, h), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE
    )
    return rotated


def preprocess_for_ocr(image_path: str | Path) -> np.ndarray:
    """Pipeline complet : preprocessing + redressement.

    C'est la fonction principale à utiliser avant l'OCR.
    """
    processed = preprocess_image(image_path)
    deskewed = deskew(processed)
    return deskewed


def preprocess_for_vision(image_path: str | Path) -> np.ndarray:
    """Preprocessing léger pour le modèle vision (classification).

    Le modèle vision n'a pas besoin de binarisation, juste d'une
    image propre et bien contrastée.
    """
    img = cv2.imread(str(image_path))
    if img is None:
        raise FileNotFoundError(f"Impossible de lire l'image: {image_path}")

    # Redimensionner si trop grand (le modèle vision a une limite)
    h, w = img.shape[:2]
    max_dim = 2048
    if max(h, w) > max_dim:
        scale = max_dim / max(h, w)
        img = cv2.resize(img, None, fx=scale, fy=scale, interpolation=cv2.INTER_AREA)

    # Léger débruitage sans perdre les détails
    denoised = cv2.fastNlMeansDenoisingColored(img, h=6, hColor=6)

    return denoised
