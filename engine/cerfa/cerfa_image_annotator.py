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

    # Certificat de conformité — Je soussigné (y=460)
    if vendeur_nom:
        draw.text((168, 460), vendeur_nom, fill=blue, font=font)

    # Certificat de vente — Je soussigné (y=1000, après le label)
    if vendeur_nom:
        # Extraire juste le nom commercial (pas le complément)
        nom_court = vendeur_nom.split(" - ")[0] if " - " in vendeur_nom else vendeur_nom
        draw.text((220, 1000), nom_court, fill=blue, font=font_big)

    # Date de vente (JJ/MM/AAAA) — cases individuelles après "désignée ci-dessous le"
    # 8 cases : J J / M M / A A A A
    # Première case à x≈340, y≈1155, espacement ~22px entre cases, séparateur / ajoute ~8px
    if date_vente and "/" in date_vente:
        parts = date_vente.split("/")
        if len(parts) == 3:
            jj, mm, aaaa = parts[0].zfill(2), parts[1].zfill(2), parts[2].zfill(4)
            date_chars = list(jj) + list(mm) + list(aaaa)
            # Positions X de chaque case (mesurées sur l'image 200dpi)
            case_x = [347, 367, 395, 415, 443, 463, 483, 503]
            for i, ch in enumerate(date_chars):
                if i < len(case_x):
                    draw.text((case_x[i], 1161), ch, fill=blue, font=font)

    # USAGE — X dans OUI (case à droite du label USAGE)
    draw.text((1225, 1018), 'X', fill=blue, font=font_big)

    # COULEUR — cocher la bonne case
    if couleur:
        couleur_lower = couleur.lower()
        couleur_cases = {
            "noir": (1177, 1050),
            "blanc": (1177, 1100),
            "gris": (1177, 1075),
            "bleu": (1350, 1050),
            "rouge": (1350, 1075),
            "vert": (1350, 1100),
        }
        pos = couleur_cases.get(couleur_lower)
        if pos:
            draw.text(pos, 'V', fill=blue, font=font)

    # CACHET et SIGNATURE — sous le label "CACHET et SIGNATURE" (y=1015)
    if cachet_nom:
        draw.rectangle([(660, 1015), (870, 1070)], outline=blue, width=2)
        draw.text((668, 1018), cachet_nom, fill=blue, font=font_stamp)
        if cachet_adresse:
            draw.text((668, 1032), cachet_adresse, fill=blue, font=font_stamp)
        if cachet_siret:
            draw.text((668, 1046), f"SIRET {cachet_siret}", fill=blue, font=font_stamp)
        draw.text((668, 1058), "~ signature numérique ~", fill=gray, font=font_stamp)

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
