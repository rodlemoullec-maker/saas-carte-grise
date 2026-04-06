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
                ImageFont.truetype(p, 22),
            )
    f = ImageFont.load_default()
    return f, f, f, f


def annotate_cerfa_vn(
    image_path: str,
    vendeur_nom: str = "",
    date_vente: str = "",  # JJ/MM/AAAA
    cachet_nom: str = "",
    cachet_adresse: str = "",
    cachet_siret: str = "",
    couleur: str = "",
    couleur_nuance: str = "",  # "clair" ou "fonce"
    usage: str = "",  # "oui" ou "non"
    personne_type: str = "",  # "physique" ou "morale"
    sexe: str = "",  # "M" ou "F"
    titulaire_nom: str = "",
    titulaire_nom_usage: str = "",
    titulaire_date_naissance: str = "",
    output_path: str | None = None,
    # Champs techniques
    date_reception: str = "",
    numero_k: str = "",
    origine_hors_ue: bool = False,
    certificat_source: str = "",  # "constructeur" ou "representant"
    marque_d1: str = "",
    type_variante_d2: str = "",
    cnit_d21: str = "",
    vin_e: str = "",
    denomination_d3: str = "",
    masse_f1: str = "",
    masse_f2: str = "",
    masse_f3: str = "",
    masse_g: str = "",
    poids_vide_g1: str = "",
    categorie_j: str = "",
    genre_j1: str = "",
    carrosserie_j2: str = "",
    carrosserie_j3: str = "",
    cylindree_p1: str = "",
    puissance_nette_p2: str = "",
    places_s1: str = "",
    places_s2: str = "",
    energie_p3: str = "",
    puissance_admin_p6: str = "",
    rapport_puiss_masse: str = "",
    niveau_sonore_u1: str = "",
    vitesse_moteur_u2: str = "",
    co2_v7: str = "",
    classe_env_v9: str = "",
) -> str:
    """
    Annote un Cerfa 13749 (VN) avec les champs manquants.
    Image attendue : 1654x2339 px (200 DPI).
    Retourne le chemin de l'image annotée.
    """
    font, font_big, font_stamp, font_xl = _get_fonts()
    black = (0, 0, 0)
    blue = (0, 51, 153)
    gray = (100, 100, 100)

    img = Image.open(image_path)
    draw = ImageDraw.Draw(img)

    def _draw_check(d, cx, cy, color=black):
        """Dessine une coche ✓ centrée sur (cx, cy)."""
        d.line([(cx-6, cy), (cx-2, cy+6)], fill=color, width=3)
        d.line([(cx-2, cy+6), (cx+8, cy-6)], fill=color, width=3)

    nom_court = vendeur_nom.split(" - ")[0] if " - " in vendeur_nom else vendeur_nom

    # Case constructeur / représentant accrédité
    if certificat_source:
        source_positions = {
            "constructeur": (1015, 394),
            "representant": (1253, 394),
        }
        pos = source_positions.get(certificat_source.lower())
        if pos:
            _draw_check(draw, pos[0], pos[1])

    # Certificat de conformité — Je soussigné (y=487, x=112)
    if vendeur_nom:
        draw.text((95, 493), nom_court, fill=black, font=font_big)

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

    # DEMANDEUR — Personne physique / morale
    if personne_type:
        personne_positions = {
            "physique": (696, 1313),
            "morale": (700, 1310),
        }
        pos = personne_positions.get(personne_type.lower())
        if pos:
            _draw_check(draw, pos[0], pos[1])

    # Sexe M/F
    if sexe:
        sexe_positions = {
            "M": (935, 1314),
            "F": (1018, 1314),
        }
        pos = sexe_positions.get(sexe.upper())
        if pos:
            _draw_check(draw, pos[0], pos[1])

    # Titulaire nom
    if titulaire_nom:
        draw.text((204, 1372), titulaire_nom, fill=black, font=font_xl)

    # Date de naissance — un chiffre par case (JJ/MM/AAAA)
    if titulaire_date_naissance and "/" in titulaire_date_naissance:
        parts = titulaire_date_naissance.split("/")
        if len(parts) == 3:
            jj, mm, aaaa = parts[0].zfill(2), parts[1].zfill(2), parts[2].zfill(4)
            date_chars = list(jj) + list(mm) + list(aaaa)
            nais_x = [189, 220, 255, 286, 325, 360, 390, 421]
            for i, ch in enumerate(date_chars):
                if i < len(nais_x):
                    draw.text((nais_x[i], 1486), ch, fill=black, font=font_xl)

    # Nom d'usage
    if titulaire_nom_usage:
        draw.text((1097, 1372), titulaire_nom_usage, fill=black, font=font_xl)

    # USAGE (OUI/NON)
    if usage:
        usage_positions = {
            "oui": (1266, 1044),
            "non": (1365, 1044),
        }
        pos = usage_positions.get(usage.lower())
        if pos:
            _draw_check(draw, pos[0], pos[1])

    # COULEUR DOMINANTE — cocher la case correspondante
    if couleur:
        couleur_positions = {
            "noir":    (1311, 1140),
            "marron":  (1311, 1171),
            "rouge":   (1311, 1202),
            "orange":  (1311, 1233),
            "jaune":   (1311, 1264),
            "vert":    (1470, 1141),
            "bleu":    (1470, 1172),
            "beige":   (1470, 1203),
            "gris":    (1470, 1234),
            "blanc":   (1470, 1265),
        }
        pos = couleur_positions.get(couleur.lower())
        if pos:
            _draw_check(draw, pos[0], pos[1])
    # Nuance CLAIR/FONCE
    if couleur_nuance:
        nuance_positions = {
            "clair": (1219, 1170),
            "fonce": (1217, 1261),
        }
        pos = nuance_positions.get(couleur_nuance.lower())
        if pos:
            _draw_check(draw, pos[0], pos[1])

    # Date de réception par type
    if date_reception:
        draw.text((319, 580), date_reception, fill=black, font=font_xl)
    # Numéro K
    if numero_k:
        draw.text((87, 671), numero_k, fill=black, font=font_xl)

    # Attestation de dédouanement — signature vendeur (hors UE uniquement)
    if origine_hors_ue:
        sig_dx, sig_dy = 200, 850
        points_dedou = [
            (sig_dx, sig_dy+10), (sig_dx+5, sig_dy+8), (sig_dx+12, sig_dy+2),
            (sig_dx+20, sig_dy-4), (sig_dx+30, sig_dy-8), (sig_dx+38, sig_dy-5),
            (sig_dx+42, sig_dy), (sig_dx+35, sig_dy+6), (sig_dx+28, sig_dy+10),
            (sig_dx+40, sig_dy+8), (sig_dx+50, sig_dy+3), (sig_dx+58, sig_dy-2),
            (sig_dx+65, sig_dy-6), (sig_dx+75, sig_dy-3), (sig_dx+80, sig_dy+2),
            (sig_dx+72, sig_dy+8), (sig_dx+78, sig_dy+6), (sig_dx+88, sig_dy+2),
            (sig_dx+95, sig_dy-1), (sig_dx+105, sig_dy+4), (sig_dx+115, sig_dy+6),
        ]
        for w in range(2):
            draw.line(points_dedou, fill=black, width=2-w, joint="curve")
        draw.arc([(sig_dx+85, sig_dy-12), (sig_dx+120, sig_dy+8)], 200, 80, fill=black, width=2)
        draw.line([(sig_dx+10, sig_dy+14), (sig_dx+110, sig_dy+12)], fill=black, width=1)

    # ─── Champs techniques du tableau véhicule (200 DPI) ───
    # Ligne Marque (D.1) — à droite du label, y≈380
    if marque_d1:
        draw.text((519, 490), marque_d1, fill=black, font=font_xl)
    # Type Variante Version (D.2) — y≈418
    if type_variante_d2:
        draw.text((519, 548), type_variante_d2, fill=black, font=font_xl)
    # Dénomination commerciale D.3
    if denomination_d3:
        draw.text((1058, 548), denomination_d3, fill=black, font=font_xl)
    # CNIT D.2.1
    if cnit_d21:
        draw.text((519, 600), cnit_d21, fill=black, font=font_xl)
    # VIN E
    if vin_e:
        draw.text((1058, 600), vin_e, fill=black, font=font_xl)
    # Masse F.1 (masse en charge max tech)
    if masse_f1:
        draw.text((518, 660), masse_f1, fill=black, font=font_xl)
    # Masse F.2 (PTAC)
    if masse_f2:
        draw.text((730, 660), masse_f2, fill=black, font=font_xl)
    # Masse F.3 (masse ensemble)
    if masse_f3:
        draw.text((943, 660), masse_f3, fill=black, font=font_xl)
    # Masse en service G
    if masse_g:
        draw.text((1163, 660), masse_g, fill=black, font=font_xl)
    # Poids vide G.1
    if poids_vide_g1:
        draw.text((1383, 660), poids_vide_g1, fill=black, font=font_xl)
    # Catégorie J
    if categorie_j:
        draw.text((520, 752), categorie_j, fill=black, font=font_xl)
    # Genre national J.1
    if genre_j1:
        draw.text((694, 752), genre_j1, fill=black, font=font_xl)
    # Carrosserie CE J.2
    if carrosserie_j2:
        draw.text((868, 752), carrosserie_j2, fill=black, font=font_xl)
    # Carte nationale J.3
    if carrosserie_j3:
        draw.text((1040, 752), carrosserie_j3, fill=black, font=font_xl)
    # Cylindrée P.1
    if cylindree_p1:
        draw.text((1215, 752), cylindree_p1, fill=black, font=font_xl)
    # Puissance nette max P.2
    if puissance_nette_p2:
        draw.text((1384, 752), puissance_nette_p2, fill=black, font=font_xl)
    # Places assises S.1
    if places_s1:
        draw.text((1170, 806), places_s1, fill=black, font=font_xl)
    # Places debout S.2
    if places_s2:
        draw.text((1390, 806), places_s2, fill=black, font=font_xl)
    # Énergie P.3
    if energie_p3:
        draw.text((517, 806), energie_p3, fill=black, font=font_xl)
    # Puissance administrative P.6
    if puissance_admin_p6:
        draw.text((730, 806), puissance_admin_p6, fill=black, font=font_xl)
    # Rapport puissance/masse (motos)
    if rapport_puiss_masse:
        draw.text((945, 806), rapport_puiss_masse, fill=black, font=font_xl)
    # Niveau sonore U.1
    if niveau_sonore_u1:
        draw.text((522, 895), niveau_sonore_u1, fill=black, font=font_xl)
    # Vitesse moteur U.2
    if vitesse_moteur_u2:
        draw.text((748, 895), vitesse_moteur_u2, fill=black, font=font_xl)
    # CO2 V.7
    if co2_v7:
        draw.text((1063, 895), co2_v7, fill=black, font=font_xl)
    # Classe environnementale V.9
    if classe_env_v9:
        draw.text((1301, 895), classe_env_v9, fill=black, font=font_xl)

    # CACHET et SIGNATURE (sous le label, y=1020)
    if cachet_nom:
        draw.rectangle([(710, 1090), (930, 1150)], outline=blue, width=2)
        draw.text((718, 1093), cachet_nom, fill=blue, font=font_stamp)
        if cachet_adresse:
            draw.text((718, 1107), cachet_adresse, fill=blue, font=font_stamp)
        if cachet_siret:
            draw.text((718, 1121), f"SIRET {cachet_siret}", fill=blue, font=font_stamp)
        # Signature manuscrite réaliste
        sig_x, sig_y = 770, 1130
        # Trait principal — boucle montante puis descendante
        points_main = [
            (sig_x, sig_y+10), (sig_x+5, sig_y+8), (sig_x+12, sig_y+2),
            (sig_x+20, sig_y-4), (sig_x+30, sig_y-8), (sig_x+38, sig_y-5),
            (sig_x+42, sig_y), (sig_x+35, sig_y+6), (sig_x+28, sig_y+10),
            (sig_x+40, sig_y+8), (sig_x+50, sig_y+3), (sig_x+58, sig_y-2),
            (sig_x+65, sig_y-6), (sig_x+75, sig_y-3), (sig_x+80, sig_y+2),
            (sig_x+72, sig_y+8), (sig_x+78, sig_y+6), (sig_x+88, sig_y+2),
            (sig_x+95, sig_y-1), (sig_x+105, sig_y+4), (sig_x+115, sig_y+6),
        ]
        for w in range(2):
            draw.line(points_main, fill=blue, width=2-w, joint="curve")
        # Boucle du paraphe
        draw.arc([(sig_x+85, sig_y-12), (sig_x+120, sig_y+8)], 200, 80, fill=blue, width=2)
        # Trait de soulignement
        draw.line([(sig_x+10, sig_y+14), (sig_x+110, sig_y+12)], fill=blue, width=1)

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
