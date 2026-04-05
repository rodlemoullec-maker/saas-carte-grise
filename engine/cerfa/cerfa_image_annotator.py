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
    black = (0, 0, 0)
    blue = (0, 51, 153)
    gray = (100, 100, 100)

    img = Image.open(image_path)
    draw = ImageDraw.Draw(img)

    nom_court = vendeur_nom.split(" - ")[0] if " - " in vendeur_nom else vendeur_nom

    # Certificat de conformité — Je soussigné (y=487, x=112)
    if vendeur_nom:
        draw.text((100, 489), nom_court, fill=black, font=font)

    # Certificat de vente — Je soussigné : (y=1047, x=95)
    if vendeur_nom:
        draw.text((95, 1047), nom_court, fill=black, font=font_big)

    # Date de vente — un chiffre par case après "désignée ci-dessous le"
    # Cases: J1 J2 | M1 M2 | A1 A2 A3 A4
    if date_vente and "/" in date_vente:
        parts = date_vente.split("/")
        if len(parts) == 3:
            jj, mm, aaaa = parts[0].zfill(2), parts[1].zfill(2), parts[2].zfill(4)
            date_chars = list(jj) + list(mm) + list(aaaa)
            # X centré dans chaque case (image 200dpi)
            case_x = [296, 323, 354, 377, 401, 428, 454, 474]
            for i, ch in enumerate(date_chars):
                if i < len(case_x):
                    draw.text((case_x[i], 1163), ch, fill=black, font=font)

    # USAGE et COULEUR — déjà cochés par Playwright, pas besoin d'annoter

    # CACHET et SIGNATURE (sous le label, y=1020)
    if cachet_nom:
        draw.rectangle([(660, 1020), (880, 1080)], outline=blue, width=2)
        draw.text((668, 1023), cachet_nom, fill=blue, font=font_stamp)
        if cachet_adresse:
            draw.text((668, 1037), cachet_adresse, fill=blue, font=font_stamp)
        if cachet_siret:
            draw.text((668, 1051), f"SIRET {cachet_siret}", fill=blue, font=font_stamp)
        draw.text((668, 1065), "Signature :", fill=blue, font=font_stamp)
        # Dessiner une signature manuscrite stylisée
        for offset in range(3):
            draw.arc([(730+offset, 1060+offset), (850+offset, 1078+offset)], 0, 180, fill=blue, width=1)
            draw.arc([(750+offset, 1062+offset), (820+offset, 1076+offset)], 180, 360, fill=blue, width=1)

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
