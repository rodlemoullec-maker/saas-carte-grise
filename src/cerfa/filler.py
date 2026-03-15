"""Pré-remplissage du CERFA 13750 par superposition de texte.

Le PDF officiel n'a pas de champs AcroForm, donc on écrit directement
le texte aux coordonnées précises sur le document avec PyMuPDF.
Les coordonnées sont calibrées sur le CERFA 13750*07 (A4, 595×842 pts).
"""

from pathlib import Path

import fitz  # PyMuPDF

from config.settings import CERFA_13750_TEMPLATE, OUTPUT_DIR

# Coordonnées des champs sur le CERFA 13750*07 (x, y en points PDF)
# Origine = coin haut-gauche. 1 pt = 1/72 inch.
# Ces coordonnées doivent être calibrées avec un vrai CERFA.
# Format : "nom_champ": (x, y, font_size)
FIELD_POSITIONS = {
    # --- Cadre demandeur ---
    "demandeur_nom": (50, 155, 9),
    "demandeur_nom_usage": (50, 175, 8),
    "demandeur_naissance_jour": (80, 192, 8),
    "demandeur_naissance_mois": (115, 192, 8),
    "demandeur_naissance_annee": (150, 192, 8),
    "demandeur_naissance_commune": (230, 192, 8),
    "demandeur_naissance_departement": (400, 192, 8),
    "demandeur_naissance_pays": (470, 192, 8),
    "demandeur_adresse_etage": (50, 222, 8),
    "demandeur_adresse_immeuble": (300, 222, 8),
    "demandeur_adresse_numero": (50, 240, 8),
    "demandeur_adresse_extension": (120, 240, 8),
    "demandeur_adresse_type_voie": (180, 240, 8),
    "demandeur_adresse_nom_voie": (240, 240, 8),
    "demandeur_adresse_lieu_dit": (50, 258, 8),
    "demandeur_adresse_code_postal": (50, 275, 9),
    "demandeur_adresse_commune": (130, 275, 9),

    # --- Cadre véhicule ---
    "immatriculation": (430, 107, 10),
    "marque": (50, 370, 9),
    "tvv_cnit": (200, 370, 9),
    "denomination_commerciale": (380, 370, 9),
    "vin": (50, 390, 9),
    "genre": (300, 390, 9),
    "carrosserie_ce": (380, 390, 9),
    "energie": (50, 410, 9),
    "puissance_fiscale": (150, 410, 9),
    "nb_places": (250, 410, 9),

    # --- Taxes ---
    "Y1": (460, 590, 9),
    "Y3": (460, 610, 9),
    "Y4": (460, 630, 9),
    "Y5": (460, 650, 9),
    "Y6": (460, 670, 9),
    "total_taxes": (460, 700, 10),
}


def fill_cerfa(
    data: dict,
    output_filename: str | None = None,
    template_path: str | Path | None = None,
) -> str:
    """Pré-remplit le CERFA 13750 avec les données fournies.

    Args:
        data: Dict avec les données à remplir.
            Les clés doivent correspondre à FIELD_POSITIONS.
        output_filename: Nom du fichier de sortie (optionnel).
        template_path: Chemin vers le template CERFA (optionnel).

    Returns:
        Chemin du fichier PDF généré.
    """
    template = Path(template_path) if template_path else CERFA_13750_TEMPLATE
    if not template.exists():
        raise FileNotFoundError(f"Template CERFA non trouvé: {template}")

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    if not output_filename:
        immat = data.get("immatriculation", "XXXX").replace("-", "").replace(" ", "")
        output_filename = f"cerfa_13750_{immat}.pdf"

    output_path = OUTPUT_DIR / output_filename

    # Ouvrir le template
    doc = fitz.open(str(template))
    page = doc[0]

    # Écrire chaque champ sur le PDF
    fields_filled = 0
    for field_name, value in data.items():
        if field_name not in FIELD_POSITIONS or not value:
            continue

        x, y, font_size = FIELD_POSITIONS[field_name]
        value_str = str(value)

        # Insérer le texte
        text_point = fitz.Point(x, y)
        page.insert_text(
            text_point,
            value_str,
            fontsize=font_size,
            fontname="helv",
            color=(0, 0, 0.6),  # Bleu foncé pour distinguer du texte imprimé
        )
        fields_filled += 1

    # Sauvegarder
    doc.save(str(output_path))
    doc.close()

    return str(output_path)


def fill_cerfa_from_dossier(
    demandeur: dict,
    vehicule: dict,
    taxes: dict,
    output_filename: str | None = None,
) -> str:
    """Pré-remplit le CERFA à partir des données structurées d'un dossier.

    Args:
        demandeur: Données du demandeur (CNI + justificatif).
        vehicule: Données du véhicule (carte grise + BDD).
        taxes: Taxes calculées.

    Returns:
        Chemin du fichier PDF généré.
    """
    data = {}

    # Demandeur
    nom = demandeur.get("nom", "")
    prenom = demandeur.get("prenom", "")
    data["demandeur_nom"] = f"{nom} {prenom}".strip().upper()
    data["demandeur_nom_usage"] = demandeur.get("nom_usage", "")

    # Date de naissance
    date_naissance = demandeur.get("date_naissance", "")
    if date_naissance and "/" in date_naissance:
        parts = date_naissance.split("/")
        if len(parts) == 3:
            data["demandeur_naissance_jour"] = parts[0]
            data["demandeur_naissance_mois"] = parts[1]
            data["demandeur_naissance_annee"] = parts[2]

    data["demandeur_naissance_commune"] = demandeur.get("lieu_naissance", "")

    # Adresse
    data["demandeur_adresse_code_postal"] = demandeur.get("adresse_code_postal", "")
    data["demandeur_adresse_commune"] = demandeur.get("adresse_ville", "")
    data["demandeur_adresse_nom_voie"] = demandeur.get("adresse_rue", "")
    data["demandeur_adresse_numero"] = demandeur.get("adresse_numero", "")

    # Véhicule
    data["immatriculation"] = vehicule.get("A_immatriculation", vehicule.get("immatriculation", ""))
    data["marque"] = vehicule.get("D1_marque", vehicule.get("marque", ""))
    data["tvv_cnit"] = vehicule.get("D2_type_variante_version", vehicule.get("cnit", ""))
    data["denomination_commerciale"] = vehicule.get("D3_denomination_commerciale", vehicule.get("denomination_commerciale", ""))
    data["vin"] = vehicule.get("E_vin", vehicule.get("vin", ""))
    data["genre"] = vehicule.get("J1_genre_national", vehicule.get("genre", ""))
    data["carrosserie_ce"] = vehicule.get("J2_carrosserie_ce", vehicule.get("carrosserie", ""))
    data["energie"] = vehicule.get("P3_energie", vehicule.get("energie", ""))
    data["puissance_fiscale"] = str(vehicule.get("P6_puissance_fiscale", vehicule.get("puissance_fiscale", "")))
    data["nb_places"] = str(vehicule.get("S1_nb_places_assises", vehicule.get("nb_places", "")))

    # Taxes
    data["Y1"] = f"{taxes.get('Y1_taxe_regionale', 0):.2f} €"
    data["Y3"] = f"{taxes.get('Y3_taxe_formation', 0):.2f} €"
    data["Y4"] = f"{taxes.get('Y4_malus_co2', 0):.2f} €"
    data["Y5"] = f"{taxes.get('Y5_malus_masse', 0):.2f} €"
    data["Y6"] = f"{taxes.get('Y6_taxe_fixe', 0):.2f} €"
    data["total_taxes"] = f"{taxes.get('total', 0):.2f} €"

    return fill_cerfa(data, output_filename)


def get_field_positions() -> dict:
    """Retourne les positions des champs (utile pour le calibrage)."""
    return FIELD_POSITIONS.copy()
