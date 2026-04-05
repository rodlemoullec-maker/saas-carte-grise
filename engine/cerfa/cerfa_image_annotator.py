"""
Annotateur d'images Cerfa — ajoute les champs manquants sur le PDF généré par Playwright.

Playwright remplit la majorité des champs via le formulaire service-public.gouv.fr,
mais certains champs (certificat de vente, cachet, signature) ne sont pas remplis
car le formulaire web a des bugs sur ces sections.

Ce script ajoute les données manquantes directement sur l'image PNG du Cerfa.

Usage :
    from engine.cerfa.cerfa_image_annotator import annotate_cerfa_vn, annotate_cerfa_vo
    annotate_cerfa_vn('cerfa.png', data)
"""
from __future__ import annotations

import logging
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

logger = logging.getLogger(__name__)

# Police par défaut
def _get_fonts():
    paths = [
        '/System/Library/Fonts/Helvetica.ttc',  # macOS
        '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',  # Linux
        'C:\\Windows\\Fonts\\arial.ttf',  # Windows
    ]
    for p in paths:
        if Path(p).exists():
            return (
                ImageFont.truetype(p, 17),
                ImageFont.truetype(p, 19),
                ImageFont.truetype(p, 12),
            )
    f = ImageFont.load_default()
    return f, f, f


def annotate_cerfa_vn(
    image_path: str,
    vendeur_nom: str = "",
    date_vente: str = "",  # JJ/MM/AAAA
    cachet_nom: str = "",
    cachet_adresse: str = "",
    cachet_siret: str = "",
    couleur: str = "",
    output_path: str | None = None,
) -> str:
    """
    Annote un Cerfa 13749 (VN) avec les champs manquants.
    Image attendue : 1654x2339 px (200 DPI).
    Retourne le chemin de l'image annotée.
    """
    font, font_big, font_stamp = _get_fonts()
    blue = (0, 51, 153)
    gray = (100, 100, 100)

    img = Image.open(image_path)
    draw = ImageDraw.Draw(img)

    # Certificat de conformité — Je soussigné
    if vendeur_nom:
        draw.text((168, 458), vendeur_nom, fill=blue, font=font)

    # Certificat de vente — Je soussigné
    if vendeur_nom:
        draw.text((215, 995), vendeur_nom, fill=blue, font=font_big)

    # Date de vente (JJ/MM/AAAA)
    if date_vente and "/" in date_vente:
        parts = date_vente.split("/")
        if len(parts) == 3:
            draw.text((148, 1065), parts[0], fill=blue, font=font)
            draw.text((228, 1065), parts[1], fill=blue, font=font)
            draw.text((325, 1065), parts[2], fill=blue, font=font)

    # USAGE — X dans OUI
    draw.text((1220, 1000), 'X', fill=blue, font=font_big)

    # COULEUR — cocher la bonne case
    if couleur:
        couleur_lower = couleur.lower()
        # Positions des cases couleur dans la grille (approximatives)
        couleur_cases = {
            "noir": (1177, 1042),
            "blanc": (1177, 1092),
            "gris": (1177, 1067),
            "bleu": (1350, 1042),
            "rouge": (1350, 1067),
            "vert": (1350, 1092),
        }
        pos = couleur_cases.get(couleur_lower)
        if pos:
            draw.text(pos, 'V', fill=blue, font=font)

    # CACHET et SIGNATURE
    if cachet_nom:
        draw.rectangle([(660, 992), (870, 1052)], outline=blue, width=2)
        draw.text((668, 995), cachet_nom, fill=blue, font=font_stamp)
        if cachet_adresse:
            draw.text((668, 1009), cachet_adresse, fill=blue, font=font_stamp)
        if cachet_siret:
            draw.text((668, 1023), f"SIRET {cachet_siret}", fill=blue, font=font_stamp)
        draw.text((668, 1037), "~ signature numérique ~", fill=gray, font=font_stamp)

    out = output_path or image_path
    img.save(out, "PNG")
    logger.info(f"[CerfaAnnotator] VN annoté : {out}")
    return out


def annotate_cerfa_vo(
    image_path: str,
    vendeur_nom: str = "",
    acheteur_nom: str = "",
    date_cession: str = "",
    cachet_nom: str = "",
    cachet_adresse: str = "",
    cachet_siret: str = "",
    output_path: str | None = None,
) -> str:
    """
    Annote un Cerfa 13750 (VO) avec les champs manquants.
    Image attendue : 200 DPI.
    """
    font, font_big, font_stamp = _get_fonts()
    blue = (0, 51, 153)
    gray = (100, 100, 100)

    img = Image.open(image_path)
    draw = ImageDraw.Draw(img)

    # Cachet + signature
    if cachet_nom:
        draw.rectangle([(660, 992), (870, 1052)], outline=blue, width=2)
        draw.text((668, 995), cachet_nom, fill=blue, font=font_stamp)
        if cachet_adresse:
            draw.text((668, 1009), cachet_adresse, fill=blue, font=font_stamp)
        if cachet_siret:
            draw.text((668, 1023), f"SIRET {cachet_siret}", fill=blue, font=font_stamp)
        draw.text((668, 1037), "~ signature numérique ~", fill=gray, font=font_stamp)

    out = output_path or image_path
    img.save(out, "PNG")
    logger.info(f"[CerfaAnnotator] VO annoté : {out}")
    return out
