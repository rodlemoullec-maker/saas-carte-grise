"""
Annotateur du Cerfa 15776*02 (Certificat de cession d'un véhicule) — 100% PIL.

Format A4 portrait, 200 DPI, dimensions 1654x2339 px.

Le Cerfa 15776 est utilisé pour les ventes de véhicules d'occasion entre
particuliers ou avec un professionnel. Il comprend trois parties :
- Identification du véhicule (marque, VIN, immat, date de mise en circulation)
- Identité de l'ancien propriétaire (vendeur)
- Identité du nouveau propriétaire (acheteur)
- Mention de cession (date, heure, lieu, signatures)

Note pour l'éditeur : les positions pixel ci-dessous sont **approximatives**
et doivent être calibrées sur l'image vierge officielle téléchargée depuis
service-public.gouv.fr (formulaire 15776*02 ou version courante).

Pour calibrer :
1. Télécharger le PDF officiel du Cerfa 15776
2. Le convertir en PNG 200 DPI (pdf2image ou ImageMagick)
3. Le placer dans site/assets/cerfa_15776_blank.png
4. Ajuster les coordonnées (x, y) ci-dessous en fonction de l'image réelle
"""
from __future__ import annotations

import logging
from pathlib import Path

from PIL import Image, ImageDraw

from engine.cerfa.cerfa_image_annotator import _get_fonts

logger = logging.getLogger(__name__)


# ─── Positions pixel (à calibrer sur image vierge officielle) ───────────────
# Section 1 — Véhicule
P_IMMATRICULATION = (200, 380)
P_VIN = (200, 440)
P_MARQUE = (200, 500)
P_TYPE_COMMERCIAL = (200, 560)
P_DATE_PREMIERE_IMMAT = (200, 620)  # JJ/MM/AAAA — texte simple
P_GENRE = (900, 620)

# Section 2 — Ancien propriétaire (vendeur)
P_VENDEUR_NOM = (200, 800)
P_VENDEUR_PRENOM = (200, 860)
P_VENDEUR_DATE_NAISSANCE = (200, 920)
P_VENDEUR_LIEU_NAISSANCE = (700, 920)
P_VENDEUR_ADRESSE = (200, 980)
P_VENDEUR_CP_VILLE = (200, 1040)

# Section 3 — Nouveau propriétaire (acheteur)
P_ACHETEUR_NOM = (200, 1240)
P_ACHETEUR_PRENOM = (200, 1300)
P_ACHETEUR_DATE_NAISSANCE = (200, 1360)
P_ACHETEUR_LIEU_NAISSANCE = (700, 1360)
P_ACHETEUR_ADRESSE = (200, 1420)
P_ACHETEUR_CP_VILLE = (200, 1480)

# Section 4 — Cession
P_DATE_CESSION = (300, 1700)
P_HEURE_CESSION = (700, 1700)
P_LIEU_CESSION = (300, 1770)

# Cachet et signature de l'agent (en bas à droite)
P_CACHET_RECT = (1100, 1900, 1500, 2100)  # rectangle x1, y1, x2, y2
P_CACHET_NOM = (1110, 1910)
P_CACHET_ADRESSE = (1110, 1940)
P_CACHET_SIRET = (1110, 1970)
P_SIGNATURE = (1110, 2020)


def annotate_cerfa_15776(
    image_path: str,
    # Véhicule
    immatriculation: str = "",
    vin: str = "",
    marque: str = "",
    type_commercial: str = "",
    date_premiere_immat: str = "",
    genre: str = "",
    # Vendeur (ancien propriétaire)
    vendeur_nom: str = "",
    vendeur_prenom: str = "",
    vendeur_date_naissance: str = "",
    vendeur_lieu_naissance: str = "",
    vendeur_adresse: str = "",
    vendeur_cp_ville: str = "",
    # Acheteur (nouveau propriétaire)
    acheteur_nom: str = "",
    acheteur_prenom: str = "",
    acheteur_date_naissance: str = "",
    acheteur_lieu_naissance: str = "",
    acheteur_adresse: str = "",
    acheteur_cp_ville: str = "",
    # Cession
    date_cession: str = "",
    heure_cession: str = "",
    lieu_cession: str = "",
    # Cachet et signature de l'agent (apposés en bas)
    cachet_nom: str = "",
    cachet_adresse: str = "",
    cachet_siret: str = "",
    signature_path: str | None = None,
    output_path: str | None = None,
) -> str:
    """
    Annote un Cerfa 15776 vierge avec les données fournies.

    Args:
        image_path : chemin vers l'image vierge du Cerfa 15776
        ... : tous les champs à inscrire
        output_path : chemin de sortie (par défaut, suffixe _generated.png)

    Returns:
        Chemin de l'image annotée
    """
    font, font_big, font_stamp, font_xl = _get_fonts()
    black = (0, 0, 0)
    blue = (0, 51, 153)

    img = Image.open(image_path)
    draw = ImageDraw.Draw(img)

    # ─── Section 1 : Véhicule ──────────────────────────────────────────
    if immatriculation:
        draw.text(P_IMMATRICULATION, immatriculation, fill=black, font=font_xl)
    if vin:
        draw.text(P_VIN, vin, fill=black, font=font_xl)
    if marque:
        draw.text(P_MARQUE, marque, fill=black, font=font_xl)
    if type_commercial:
        draw.text(P_TYPE_COMMERCIAL, type_commercial, fill=black, font=font_xl)
    if date_premiere_immat:
        draw.text(P_DATE_PREMIERE_IMMAT, date_premiere_immat, fill=black, font=font_xl)
    if genre:
        draw.text(P_GENRE, genre, fill=black, font=font_xl)

    # ─── Section 2 : Vendeur ────────────────────────────────────────────
    if vendeur_nom:
        draw.text(P_VENDEUR_NOM, vendeur_nom, fill=black, font=font_xl)
    if vendeur_prenom:
        draw.text(P_VENDEUR_PRENOM, vendeur_prenom, fill=black, font=font_xl)
    if vendeur_date_naissance:
        draw.text(P_VENDEUR_DATE_NAISSANCE, vendeur_date_naissance, fill=black, font=font_xl)
    if vendeur_lieu_naissance:
        draw.text(P_VENDEUR_LIEU_NAISSANCE, vendeur_lieu_naissance, fill=black, font=font_xl)
    if vendeur_adresse:
        draw.text(P_VENDEUR_ADRESSE, vendeur_adresse, fill=black, font=font_xl)
    if vendeur_cp_ville:
        draw.text(P_VENDEUR_CP_VILLE, vendeur_cp_ville, fill=black, font=font_xl)

    # ─── Section 3 : Acheteur ───────────────────────────────────────────
    if acheteur_nom:
        draw.text(P_ACHETEUR_NOM, acheteur_nom, fill=black, font=font_xl)
    if acheteur_prenom:
        draw.text(P_ACHETEUR_PRENOM, acheteur_prenom, fill=black, font=font_xl)
    if acheteur_date_naissance:
        draw.text(P_ACHETEUR_DATE_NAISSANCE, acheteur_date_naissance, fill=black, font=font_xl)
    if acheteur_lieu_naissance:
        draw.text(P_ACHETEUR_LIEU_NAISSANCE, acheteur_lieu_naissance, fill=black, font=font_xl)
    if acheteur_adresse:
        draw.text(P_ACHETEUR_ADRESSE, acheteur_adresse, fill=black, font=font_xl)
    if acheteur_cp_ville:
        draw.text(P_ACHETEUR_CP_VILLE, acheteur_cp_ville, fill=black, font=font_xl)

    # ─── Section 4 : Cession ────────────────────────────────────────────
    if date_cession:
        draw.text(P_DATE_CESSION, date_cession, fill=black, font=font_xl)
    if heure_cession:
        draw.text(P_HEURE_CESSION, heure_cession, fill=black, font=font_xl)
    if lieu_cession:
        draw.text(P_LIEU_CESSION, lieu_cession, fill=black, font=font_xl)

    # ─── Cachet de l'agent (en bas à droite) ────────────────────────────
    if cachet_nom or cachet_adresse or cachet_siret:
        # Encadrement du cachet
        draw.rectangle(P_CACHET_RECT, outline=blue, width=2)
        if cachet_nom:
            draw.text(P_CACHET_NOM, cachet_nom, fill=blue, font=font_stamp)
        if cachet_adresse:
            draw.text(P_CACHET_ADRESSE, cachet_adresse, fill=blue, font=font_stamp)
        if cachet_siret:
            draw.text(P_CACHET_SIRET, f"SIRET: {cachet_siret}", fill=blue, font=font_stamp)

    # Signature de l'agent (image PNG)
    if signature_path and Path(signature_path).exists():
        try:
            sig = Image.open(signature_path)
            # Redimensionner la signature pour qu'elle tienne dans la zone
            sig.thumbnail((250, 80))
            img.paste(sig, P_SIGNATURE, sig if sig.mode == "RGBA" else None)
        except Exception as e:
            logger.warning(f"[Cerfa 15776] Impossible d'ajouter la signature : {e}")

    # ─── Sauvegarde ─────────────────────────────────────────────────────
    out = output_path or str(Path(image_path).parent / "cerfa_15776_generated.png")
    img.save(out, "PNG", optimize=True)
    logger.info(f"[Cerfa 15776] Annoté → {out}")
    return out
