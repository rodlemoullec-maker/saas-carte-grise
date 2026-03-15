"""Pipeline complète : email → classification → OCR → extraction → CERFA.

Orchestre l'ensemble du flux de traitement d'un dossier carte grise.
En phase de développement, c'est ce module qui coordonne.
En production, OpenClaw prendra le relais.
"""

import json
import sys
from datetime import datetime
from pathlib import Path

from sqlalchemy import create_engine, text

from config.settings import DATABASE_URL, DOSSIERS_DIR

_engine = None


def _get_engine():
    global _engine
    if _engine is None:
        _engine = create_engine(DATABASE_URL)
    return _engine


def create_dossier(
    reference: str,
    email_source: str,
    client_nom: str = "",
    client_email: str = "",
) -> int:
    """Crée un dossier en base de données.

    Returns:
        ID du dossier créé.
    """
    engine = _get_engine()
    with engine.connect() as conn:
        result = conn.execute(
            text(
                "INSERT INTO dossiers (reference, email_source, client_nom, client_email) "
                "VALUES (:ref, :email, :nom, :client_email) RETURNING id"
            ),
            {
                "ref": reference,
                "email": email_source,
                "nom": client_nom,
                "client_email": client_email,
            },
        )
        dossier_id = result.scalar()
        conn.commit()
        return dossier_id


def add_document(
    dossier_id: int,
    type_document: str,
    fichier_path: str,
    donnees_json: dict | None = None,
    confidence: float = 0.0,
    ocr_texte_brut: str = "",
) -> int:
    """Ajoute un document à un dossier.

    Returns:
        ID du document créé.
    """
    engine = _get_engine()
    with engine.connect() as conn:
        result = conn.execute(
            text(
                "INSERT INTO documents (dossier_id, type_document, fichier_path, "
                "donnees_json, confidence, ocr_texte_brut) "
                "VALUES (:did, :type, :path, :data, :conf, :ocr) RETURNING id"
            ),
            {
                "did": dossier_id,
                "type": type_document,
                "path": fichier_path,
                "data": json.dumps(donnees_json or {}, ensure_ascii=False),
                "conf": confidence,
                "ocr": ocr_texte_brut,
            },
        )
        doc_id = result.scalar()
        conn.commit()
        return doc_id


def update_dossier_status(dossier_id: int, statut: str) -> None:
    """Met à jour le statut d'un dossier."""
    engine = _get_engine()
    with engine.connect() as conn:
        conn.execute(
            text("UPDATE dossiers SET statut = :statut WHERE id = :id"),
            {"statut": statut, "id": dossier_id},
        )
        conn.commit()


def update_dossier_data(
    dossier_id: int,
    immatriculation: str = "",
    vin: str = "",
    donnees_extraites: dict | None = None,
    taxes: dict | None = None,
    cerfa_path: str = "",
) -> None:
    """Met à jour les données d'un dossier après traitement."""
    engine = _get_engine()
    updates = []
    params = {"id": dossier_id}

    if immatriculation:
        updates.append("immatriculation = :immat")
        params["immat"] = immatriculation
    if vin:
        updates.append("vin = :vin")
        params["vin"] = vin
    if donnees_extraites:
        updates.append("donnees_extraites = :data")
        params["data"] = json.dumps(donnees_extraites, ensure_ascii=False)
    if taxes:
        updates.append("taxes = :taxes")
        params["taxes"] = json.dumps(taxes, ensure_ascii=False)
    if cerfa_path:
        updates.append("cerfa_path = :cerfa")
        params["cerfa"] = cerfa_path

    if not updates:
        return

    query = f"UPDATE dossiers SET {', '.join(updates)} WHERE id = :id"
    with engine.connect() as conn:
        conn.execute(text(query), params)
        conn.commit()


def get_dossier(dossier_id: int) -> dict | None:
    """Récupère un dossier par ID."""
    engine = _get_engine()
    with engine.connect() as conn:
        result = conn.execute(
            text("SELECT * FROM dossiers WHERE id = :id"),
            {"id": dossier_id},
        )
        row = result.mappings().fetchone()
        return dict(row) if row else None


def get_dossiers_by_status(statut: str) -> list[dict]:
    """Liste les dossiers par statut."""
    engine = _get_engine()
    with engine.connect() as conn:
        result = conn.execute(
            text("SELECT * FROM dossiers WHERE statut = :statut ORDER BY created_at DESC"),
            {"statut": statut},
        )
        return [dict(row) for row in result.mappings().fetchall()]


def get_documents_for_dossier(dossier_id: int) -> list[dict]:
    """Récupère tous les documents d'un dossier."""
    engine = _get_engine()
    with engine.connect() as conn:
        result = conn.execute(
            text("SELECT * FROM documents WHERE dossier_id = :did ORDER BY created_at"),
            {"did": dossier_id},
        )
        return [dict(row) for row in result.mappings().fetchall()]


def process_dossier(dossier_path: str | Path) -> dict:
    """Traite un dossier complet : classification → OCR → extraction → validation → taxes → CERFA.

    C'est la fonction principale qui orchestre le flux.

    Args:
        dossier_path: Chemin vers le répertoire contenant les documents.

    Returns:
        Dict avec le résultat du traitement.
    """
    from src.classification.classifier import classify_document
    from src.ocr.preprocessor import preprocess_for_ocr
    from src.ocr.engine import extract_text_from_array
    from src.extraction.carte_grise import CarteGriseExtractor
    from src.extraction.cni import CNIExtractor
    from src.extraction.cession import CessionExtractor
    from src.extraction.justificatif import JustificatifExtractor
    from src.extraction.controle_technique import ControleTechniqueExtractor
    from src.extraction.conformite import ConformiteExtractor
    from src.extraction.permis import PermisExtractor
    from src.vehicle.search import search as search_vehicle
    from src.validation.cross_checker import validate_dossier
    from src.taxes.calculator import calculer_taxes
    from src.cerfa.filler import fill_cerfa_from_dossier

    EXTRACTORS = {
        "carte_grise": CarteGriseExtractor(),
        "cni": CNIExtractor(),
        "passeport": CNIExtractor(),
        "certificat_cession": CessionExtractor(),
        "justificatif_domicile": JustificatifExtractor(),
        "controle_technique": ControleTechniqueExtractor(),
        "certificat_conformite": ConformiteExtractor(),
        "permis_conduire": PermisExtractor(),
    }

    dossier_path = Path(dossier_path)
    reference = dossier_path.name

    # Créer le dossier en BDD
    dossier_id = create_dossier(reference=reference, email_source="")
    update_dossier_status(dossier_id, "en_cours")

    # Lister les fichiers images/PDF
    extensions = {".pdf", ".jpg", ".jpeg", ".png", ".tif", ".tiff", ".bmp"}
    files = [f for f in dossier_path.iterdir() if f.suffix.lower() in extensions]

    if not files:
        update_dossier_status(dossier_id, "documents_manquants")
        return {"error": "Aucun document trouvé", "dossier_id": dossier_id}

    # Traiter chaque document
    documents_extraits = {}

    for filepath in files:
        # 1. Classification
        classification = classify_document(filepath)
        doc_type = classification["type"]
        confidence = classification["confidence"]

        # 2. OCR
        processed = preprocess_for_ocr(filepath)
        ocr_result = extract_text_from_array(processed)

        # 3. Extraction structurée
        extracted_data = {}
        if doc_type in EXTRACTORS:
            extracted_data = EXTRACTORS[doc_type].extract(ocr_result["text"])

        # Sauvegarder en BDD
        add_document(
            dossier_id=dossier_id,
            type_document=doc_type,
            fichier_path=str(filepath),
            donnees_json=extracted_data,
            confidence=confidence,
            ocr_texte_brut=ocr_result["text"],
        )

        documents_extraits[doc_type] = extracted_data

    # 4. Recherche véhicule
    cg_data = documents_extraits.get("carte_grise", {})
    coc_data = documents_extraits.get("certificat_conformite", {})

    vehicle_data = search_vehicle(
        vin=cg_data.get("E_vin", ""),
        immatriculation=cg_data.get("A_immatriculation", ""),
        cnit=cg_data.get("D2_1_cnit", ""),
        tvv=cg_data.get("D2_type_variante_version", ""),
        marque=cg_data.get("D1_marque", ""),
    )

    # 4b. Compléter avec le COC si le véhicule n'est pas dans la base
    if "types_mines" not in vehicle_data.get("sources", []) and coc_data:
        # Le COC fournit les données techniques manquantes
        for coc_key, cg_key in [
            ("cylindree", "P1_cylindree"),
            ("puissance_kw", "P2_puissance_kw"),
            ("energie", "P3_energie"),
            ("puissance_fiscale", "P6_puissance_fiscale"),
            ("genre_national", "J1_genre_national"),
            ("nb_places_assises", "S1_nb_places_assises"),
            ("ptac", "F2_ptac"),
            ("ptra", "G1_ptra"),
            ("masse_max_charge", "F1_masse_max_charge"),
            ("co2", "V7_co2"),
            ("carrosserie", "J2_carrosserie_ce"),
        ]:
            coc_val = coc_data.get(coc_key)
            if coc_val and str(coc_val).strip() not in ("", "null", "None"):
                if not cg_data.get(cg_key) or str(cg_data[cg_key]).strip() in ("", "null", "None"):
                    cg_data[cg_key] = coc_val

    # 4c. Auto-enrichissement — sauvegarder en BDD si véhicule inconnu
    if "types_mines" not in vehicle_data.get("sources", []):
        cnit = cg_data.get("D2_1_cnit", "") or cg_data.get("D2_type_variante_version", "")
        if cnit:
            from src.vehicle.types_mines import auto_enrich
            auto_enrich(
                cnit=cnit,
                marque=cg_data.get("D1_marque", ""),
                denomination=cg_data.get("D3_denomination_commerciale", ""),
                genre=cg_data.get("J1_genre_national", ""),
                carrosserie=cg_data.get("J2_carrosserie_ce", ""),
                energie=cg_data.get("P3_energie", ""),
                cylindree=int(cg_data["P1_cylindree"]) if cg_data.get("P1_cylindree") else None,
                puissance_fiscale=int(cg_data["P6_puissance_fiscale"]) if cg_data.get("P6_puissance_fiscale") else None,
                puissance_kw=float(cg_data["P2_puissance_kw"]) if cg_data.get("P2_puissance_kw") else None,
                co2=int(cg_data["V7_co2"]) if cg_data.get("V7_co2") else None,
                ptac=int(cg_data["F2_ptac"]) if cg_data.get("F2_ptac") else None,
            )

    # 5. Cross-validation
    genre = vehicle_data.get("genre", cg_data.get("J1_genre_national", "VP"))
    vehicle_in_db = "types_mines" in vehicle_data.get("sources", [])
    validation = validate_dossier(
        documents_extraits,
        genre_vehicule=genre,
        vehicle_found_in_db=vehicle_in_db,
        vehicle_data=vehicle_data,
    )

    if not validation.is_valid:
        update_dossier_status(dossier_id, "documents_manquants")
        update_dossier_data(
            dossier_id,
            immatriculation=cg_data.get("A_immatriculation", ""),
            vin=cg_data.get("E_vin", ""),
            donnees_extraites=documents_extraits,
        )
        return {
            "dossier_id": dossier_id,
            "reference": reference,
            "status": "documents_manquants",
            "validation": validation.to_dict(),
        }

    # 6. Calcul taxes
    taxes = calculer_taxes(
        puissance_fiscale=int(vehicle_data.get("puissance_fiscale") or cg_data.get("P6_puissance_fiscale") or 0),
        region="ile_de_france",  # TODO: détecter la région depuis l'adresse
        energie=vehicle_data.get("energie", cg_data.get("P3_energie", "")),
        co2=int(vehicle_data.get("co2") or cg_data.get("V7_co2") or 0),
        masse=int(vehicle_data.get("poids_vide") or 0),
        genre=genre,
        est_neuf=False,  # Occasion par défaut
    )

    # 7. Pré-remplissage CERFA
    cni_data = documents_extraits.get("cni", {})
    justif_data = documents_extraits.get("justificatif_domicile", {})

    demandeur = {
        "nom": cni_data.get("nom", ""),
        "prenom": cni_data.get("prenom", ""),
        "date_naissance": cni_data.get("date_naissance", ""),
        "lieu_naissance": cni_data.get("lieu_naissance", ""),
        "adresse_numero": justif_data.get("adresse_numero", ""),
        "adresse_rue": justif_data.get("adresse_rue", ""),
        "adresse_code_postal": justif_data.get("adresse_code_postal", ""),
        "adresse_ville": justif_data.get("adresse_ville", ""),
    }

    cerfa_path = fill_cerfa_from_dossier(demandeur, {**cg_data, **vehicle_data}, taxes)

    # 8. Mettre à jour le dossier
    update_dossier_status(dossier_id, "pret")
    update_dossier_data(
        dossier_id,
        immatriculation=cg_data.get("A_immatriculation", ""),
        vin=cg_data.get("E_vin", ""),
        donnees_extraites=documents_extraits,
        taxes=taxes,
        cerfa_path=cerfa_path,
    )

    return {
        "dossier_id": dossier_id,
        "reference": reference,
        "status": "pret",
        "immatriculation": cg_data.get("A_immatriculation", ""),
        "vehicule": {
            "marque": vehicle_data.get("marque", ""),
            "denomination": vehicle_data.get("denomination_commerciale", ""),
            "genre": genre,
        },
        "taxes": taxes,
        "cerfa_path": cerfa_path,
        "validation": validation.to_dict(),
    }
