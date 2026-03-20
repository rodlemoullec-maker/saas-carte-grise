"""Pre-remplissage du CERFA 13750 par superposition de texte.

Coordonnees calibrees sur cerfa_13750_07.pdf (595.3 x 841.9 pts).
Positions mesurees depuis les lignes et cases du template PDF.
"""

from pathlib import Path

import fitz  # PyMuPDF

from config.settings import CERFA_13750_TEMPLATE, OUTPUT_DIR

# Positions mesurees sur le template PDF
# insert_text place le BAS du texte (baseline) a la position y donnee
FIELD_POSITIONS = {
    # --- Case "Certificat" (carre x=148-163 y=74-84) ---
    "check_certificat": (151, 83, 10),

    # --- Cadre VEHICULE ---
    "immatriculation": (34, 135, 9),
    # Date d'achat : 8 cases (cases mesurees x=165-285, y=127-139)
    # Couleur dominante (cases a cocher)
    "check_couleur_noir": (424, 209, 8),
    "check_couleur_jaune": (470, 209, 8),
    "check_couleur_gris": (513, 209, 8),
    "check_couleur_marron": (424, 222, 8),
    "check_couleur_vert": (470, 222, 8),
    "check_couleur_blanc": (513, 222, 8),
    "check_couleur_rouge": (424, 236, 8),
    "check_couleur_bleu": (470, 236, 8),
    "check_couleur_orange": (424, 250, 8),
    "check_couleur_beige": (470, 250, 8),
    "check_couleur_clair": (377, 218, 8),
    "check_couleur_fonce": (377, 243, 8),

    "date_achat_j1": (168, 137, 9),
    "date_achat_j2": (182, 137, 9),
    "date_achat_m1": (199, 137, 9),
    "date_achat_m2": (213, 137, 9),
    "date_achat_a1": (231, 137, 9),
    "date_achat_a2": (245, 137, 9),
    "date_achat_a3": (259, 137, 9),
    "date_achat_a4": (273, 137, 9),
    # (I) Date certificat actuel : 8 cases (x=303-423)
    "date_certif_j1": (306, 137, 9),
    "date_certif_j2": (320, 137, 9),
    "date_certif_m1": (337, 137, 9),
    "date_certif_m2": (351, 137, 9),
    "date_certif_a1": (369, 137, 9),
    "date_certif_a2": (383, 137, 9),
    "date_certif_a3": (397, 137, 9),
    "date_certif_a4": (411, 137, 9),
    # (B) Date 1ere immatriculation : 8 cases (x=441-560)
    "date_1immat_j1": (444, 137, 9),
    "date_1immat_j2": (458, 137, 9),
    "date_1immat_m1": (475, 137, 9),
    "date_1immat_m2": (489, 137, 9),
    "date_1immat_a1": (507, 137, 9),
    "date_1immat_a2": (521, 137, 9),
    "date_1immat_a3": (535, 137, 9),
    "date_1immat_a4": (549, 137, 9),
    "marque": (34, 185, 9),
    "denomination_commerciale": (230, 185, 9),
    "tvv_cnit": (34, 206, 9),
    "vin": (34, 227, 9),
    "genre": (270, 227, 9),

    # --- Cadre TITULAIRE ---
    "check_personne_physique": (208, 304, 8),
    "check_sexe_m": (262, 304, 8),
    "check_sexe_f": (286, 304, 8),
    "titulaire_nom_prenom": (90, 319, 9),
    "titulaire_nom_usage": (395, 319, 8),
    # Date naissance : cases mesurees (y=333.5-338.9)
    "naissance_jour_1": (59, 338, 8),
    "naissance_jour_2": (70, 338, 8),
    "naissance_mois_1": (85, 338, 8),
    "naissance_mois_2": (96, 338, 8),
    "naissance_annee_1": (111, 338, 8),
    "naissance_annee_2": (122, 338, 8),
    "naissance_annee_3": (133, 338, 8),
    "naissance_annee_4": (145, 338, 8),
    "naissance_commune": (172, 338, 9),
    # Departement naissance : 3 cases (x=378.6-412.6)
    "naissance_dept_1": (381, 338, 8),
    "naissance_dept_2": (393, 338, 8),
    "naissance_dept_3": (404, 338, 8),
    "naissance_pays": (425, 338, 9),
    # Adresse : ecrire AU-DESSUS des lignes horizontales
    # Etage (ligne a y=357.9)
    "adresse_etage": (84, 356, 8),
    "adresse_immeuble": (325, 356, 8),
    # N° voie / type voie / libelle (ligne a y=372.8)
    "adresse_numero": (84, 371, 8),
    "adresse_extension": (133, 371, 8),
    "adresse_type_voie": (189, 371, 8),
    "adresse_nom_voie": (273, 371, 8),
    # Lieu-dit (ligne a y=387.6)
    "adresse_lieu_dit": (84, 386, 8),
    "adresse_telephone": (348, 386, 8),
    # Code postal : 5 cases (x=83.9-140.5, ligne a y=404.2)
    "adresse_cp_1": (86, 403, 8),
    "adresse_cp_2": (97, 403, 8),
    "adresse_cp_3": (109, 403, 8),
    "adresse_cp_4": (120, 403, 8),
    "adresse_cp_5": (131, 403, 8),
    "adresse_commune": (149, 403, 9),
}


def fill_cerfa(
    data: dict,
    output_filename: str | None = None,
    template_path: str | Path | None = None,
) -> str:
    """Pre-remplit le CERFA 13750."""
    template = Path(template_path) if template_path else CERFA_13750_TEMPLATE
    if not template.exists():
        raise FileNotFoundError(f"Template CERFA non trouve: {template}")

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    if not output_filename:
        immat = data.get("immatriculation", "XXXX").replace("-", "").replace(" ", "")
        output_filename = f"cerfa_13750_{immat}.pdf"

    output_path = OUTPUT_DIR / output_filename

    doc = fitz.open(str(template))
    page = doc[0]

    for field_name, value in data.items():
        if field_name not in FIELD_POSITIONS or not value:
            continue

        x, y, font_size = FIELD_POSITIONS[field_name]
        value_str = str(value)

        if field_name.startswith("check_"):
            value_str = "X"
            font_size = 12

        page.insert_text(
            fitz.Point(x, y),
            value_str,
            fontsize=font_size,
            fontname="helv",
            color=(0, 0, 0.6),
        )

    doc.save(str(output_path))
    doc.close()
    return str(output_path)


def _split_date(date_str: str) -> dict:
    """Decoupe une date JJ/MM/AAAA en chiffres individuels."""
    result = {}
    if not date_str or "/" not in date_str:
        return result
    parts = date_str.split("/")
    if len(parts) != 3:
        return result
    jour = parts[0].zfill(2)
    mois = parts[1].zfill(2)
    annee = parts[2].zfill(4)
    return {"j1": jour[0], "j2": jour[1], "m1": mois[0], "m2": mois[1],
            "a1": annee[0], "a2": annee[1], "a3": annee[2], "a4": annee[3]}


def fill_cerfa_from_dossier(
    demandeur: dict,
    vehicule: dict,
    taxes: dict,
    output_filename: str | None = None,
) -> str:
    """Pre-remplit le CERFA a partir des donnees d'un dossier."""
    data = {}

    # Case Certificat
    data["check_certificat"] = "X"

    # Vehicule
    data["immatriculation"] = vehicule.get("immatriculation", "")
    data["marque"] = vehicule.get("marque", "")
    data["denomination_commerciale"] = vehicule.get("denomination_commerciale", "")
    data["tvv_cnit"] = vehicule.get("cnit", "")
    data["vin"] = vehicule.get("vin", "")
    data["genre"] = vehicule.get("genre", "")

    # Date d'achat en cases individuelles
    date_achat = demandeur.get("date_cession", vehicule.get("date_cession", ""))
    for k, v in _split_date(date_achat).items():
        data[f"date_achat_{k}"] = v

    # Date certificat actuel (depuis carte grise vendeur)
    date_certif = vehicule.get("date_certificat_actuel", vehicule.get("I_date_immatriculation", ""))
    for k, v in _split_date(date_certif).items():
        data[f"date_certif_{k}"] = v

    # Date 1ere immatriculation (depuis carte grise vendeur)
    date_1immat = vehicule.get("date_premiere_immat", vehicule.get("B_date_premiere_immat", ""))
    for k, v in _split_date(date_1immat).items():
        data[f"date_1immat_{k}"] = v

    # Titulaire
    data["check_personne_physique"] = "X"
    nom = demandeur.get("nom", "")
    prenom = demandeur.get("prenom", "")
    data["titulaire_nom_prenom"] = f"{nom} {prenom}".strip().upper()

    sexe = demandeur.get("sexe", "")
    if sexe and sexe.upper() in ("M", "MASCULIN"):
        data["check_sexe_m"] = "X"
    elif sexe and sexe.upper() in ("F", "FEMININ"):
        data["check_sexe_f"] = "X"

    # Date naissance en cases individuelles
    dn = _split_date(demandeur.get("date_naissance", ""))
    for k, v in dn.items():
        data[f"naissance_{k.replace('j', 'jour_').replace('m', 'mois_').replace('a', 'annee_')}"] = v
    # Correction des cles
    for old, new in [("jour_1", "jour_1"), ("jour_2", "jour_2"),
                     ("mois_1", "mois_1"), ("mois_2", "mois_2")]:
        pass  # deja bon

    # Plus simple : remplir directement
    date_n = demandeur.get("date_naissance", "")
    if date_n and "/" in date_n:
        parts = date_n.split("/")
        if len(parts) == 3:
            jour = parts[0].zfill(2)
            mois = parts[1].zfill(2)
            annee = parts[2].zfill(4)
            data["naissance_jour_1"] = jour[0]
            data["naissance_jour_2"] = jour[1]
            data["naissance_mois_1"] = mois[0]
            data["naissance_mois_2"] = mois[1]
            data["naissance_annee_1"] = annee[0]
            data["naissance_annee_2"] = annee[1]
            data["naissance_annee_3"] = annee[2]
            data["naissance_annee_4"] = annee[3]

    data["naissance_commune"] = demandeur.get("lieu_naissance", "")
    data["naissance_pays"] = demandeur.get("lieu_naissance_pays", "FRANCE")

    # Departement de naissance
    dept_naissance = demandeur.get("lieu_naissance_departement", "")
    if not dept_naissance:
        commune = (demandeur.get("lieu_naissance") or "").upper().strip()
        COMMUNE_DEPT = {
            "PARIS": "75", "MARSEILLE": "13", "LYON": "69", "TOULOUSE": "31",
            "NICE": "06", "NANTES": "44", "MONTPELLIER": "34", "STRASBOURG": "67",
            "BORDEAUX": "33", "LILLE": "59", "RENNES": "35", "REIMS": "51",
            "TOULON": "83", "GRENOBLE": "38", "DIJON": "21", "ANGERS": "49",
            "NIMES": "30", "CLERMONT-FERRAND": "63", "TOURS": "37", "AMIENS": "80",
            "LIMOGES": "87", "METZ": "57", "BESANCON": "25", "ORLEANS": "45",
            "ROUEN": "76", "CAEN": "14", "NANCY": "54", "PERPIGNAN": "66",
            "POITIERS": "86", "PAU": "64", "CALAIS": "62", "BREST": "29",
            "LE HAVRE": "76", "LE MANS": "72", "AJACCIO": "2A", "BASTIA": "2B",
            "MULHOUSE": "68", "VALENCE": "26", "TROYES": "10",
            "AVIGNON": "84", "DUNKERQUE": "59", "LA ROCHELLE": "17",
            "SAINT-ETIENNE": "42", "SAINT-DENIS": "93",
            "LES ANDELYS": "27", "EVREUX": "27", "VERNON": "27",
        }
        dept_naissance = COMMUNE_DEPT.get(commune, "")

    if dept_naissance:
        dept_naissance = dept_naissance.strip()
        if len(dept_naissance) == 2 and dept_naissance.isdigit():
            dept_naissance = "0" + dept_naissance
        for i, char in enumerate(dept_naissance[:3]):
            data[f"naissance_dept_{i+1}"] = char

    # Adresse decomposee
    data["adresse_numero"] = demandeur.get("adresse_numero", "")
    data["adresse_type_voie"] = demandeur.get("adresse_type_voie", "")
    data["adresse_nom_voie"] = demandeur.get("adresse_nom_voie", "")

    # Code postal en cases individuelles
    cp = demandeur.get("adresse_code_postal", "")
    if cp:
        cp = cp.zfill(5)
        for i, c in enumerate(cp[:5]):
            data[f"adresse_cp_{i+1}"] = c

    data["adresse_commune"] = demandeur.get("adresse_ville", "")

    # Couleur dominante
    couleur = vehicule.get("couleur", "")
    if couleur:
        data[f"check_couleur_{couleur}"] = "X"
    teinte = vehicule.get("teinte", "")
    if teinte:
        data[f"check_couleur_{teinte}"] = "X"

    return fill_cerfa(data, output_filename)
