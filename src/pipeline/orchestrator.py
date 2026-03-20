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


def delete_dossier(dossier_id: int) -> None:
    """Supprime un dossier et ses documents de la base."""
    engine = _get_engine()
    with engine.connect() as conn:
        conn.execute(text("DELETE FROM documents WHERE dossier_id = :id"), {"id": dossier_id})
        conn.execute(text("DELETE FROM dossiers WHERE id = :id"), {"id": dossier_id})
        conn.commit()


def search_dossiers(query: str) -> list[dict]:
    """Recherche des dossiers par nom client, reference ou immatriculation."""
    engine = _get_engine()
    with engine.connect() as conn:
        result = conn.execute(
            text(
                "SELECT * FROM dossiers "
                "WHERE UPPER(client_nom) LIKE UPPER(:q) "
                "OR UPPER(reference) LIKE UPPER(:q) "
                "OR UPPER(immatriculation) LIKE UPPER(:q) "
                "ORDER BY created_at DESC LIMIT 50"
            ),
            {"q": f"%{query.strip()}%"},
        )
        return [dict(row) for row in result.mappings().fetchall()]


def get_all_dossiers() -> list[dict]:
    """Liste tous les dossiers, les plus recents en premier."""
    engine = _get_engine()
    with engine.connect() as conn:
        result = conn.execute(
            text("SELECT * FROM dossiers ORDER BY created_at DESC LIMIT 100"),
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


def process_dossier(
    dossier_path: str | Path,
    vehicle_override: dict | None = None,
    pre_extracted: dict | None = None,
) -> dict:
    """Traite un dossier : validation → taxes → CERFA.

    Si pre_extracted est fourni (données de la pré-analyse du dashboard),
    saute les étapes classification/OCR/extraction et utilise directement
    ces données. Sinon, fait tout depuis zéro.

    Args:
        dossier_path: Chemin vers le répertoire contenant les documents.
        vehicle_override: Données véhicule sélectionné manuellement.
        pre_extracted: Dict {doc_type: donnees_extraites} de la pré-analyse.
    """
    from src.validation.cross_checker import validate_dossier
    from src.taxes.calculator import calculer_taxes
    from src.cerfa.filler import fill_cerfa_from_dossier

    dossier_path = Path(dossier_path)
    reference = dossier_path.name

    # Créer le dossier en BDD
    dossier_id = create_dossier(reference=reference, email_source="")
    update_dossier_status(dossier_id, "en_cours")

    # Lister les fichiers
    extensions = {".pdf", ".jpg", ".jpeg", ".png", ".tif", ".tiff", ".bmp"}
    files = [f for f in dossier_path.iterdir() if f.suffix.lower() in extensions]

    if not files and not pre_extracted:
        update_dossier_status(dossier_id, "documents_manquants")
        return {"error": "Aucun document trouvé", "dossier_id": dossier_id}

    # Utiliser les données pré-extraites si disponibles
    if pre_extracted:
        documents_extraits = dict(pre_extracted)
        # Sauvegarder chaque document en BDD
        for doc_type, extracted_data in documents_extraits.items():
            filepath = ""
            for f in files:
                filepath = str(f)
                break
            add_document(
                dossier_id=dossier_id,
                type_document=doc_type,
                fichier_path=filepath,
                donnees_json=extracted_data,
                confidence=1.0,
            )
    else:
        # Pas de pré-analyse : faire classification + OCR + extraction
        from src.classification.classifier import classify_document
        from src.ocr.preprocessor import preprocess_for_ocr
        from src.ocr.engine import extract_text_from_array
        from src.extraction.cni import CNIExtractor
        from src.extraction.cession import CessionExtractor
        from src.extraction.justificatif import JustificatifExtractor

        EXTRACTORS = {
            "cni": CNIExtractor(),
            "passeport": CNIExtractor(),
            "certificat_cession": CessionExtractor(),
            "justificatif_domicile": JustificatifExtractor(),
        }

        documents_extraits = {}
        for filepath in files:
            classification = classify_document(filepath)
            doc_type = classification["type"]
            confidence = classification["confidence"]

            processed = preprocess_for_ocr(filepath)
            ocr_result = extract_text_from_array(processed)

            extracted_data = {}
            if doc_type in EXTRACTORS:
                extracted_data = EXTRACTORS[doc_type].extract(ocr_result["text"])

            add_document(
                dossier_id=dossier_id,
                type_document=doc_type,
                fichier_path=str(filepath),
                donnees_json=extracted_data,
                confidence=confidence,
                ocr_texte_brut=ocr_result.get("text", ""),
            )
            documents_extraits[doc_type] = extracted_data

    # 4. Données véhicule
    cession_data = documents_extraits.get("certificat_cession", {})

    if vehicle_override:
        vehicle_data = {
            "vin": cession_data.get("vin", ""),
            "immatriculation": cession_data.get("immatriculation", ""),
            "sources": ["types_mines", "selection_manuelle"],
            "cnit": vehicle_override.get("cnit", ""),
            "marque": vehicle_override.get("marque", ""),
            "denomination_commerciale": vehicle_override.get("denomination_commerciale", ""),
            "genre": vehicle_override.get("genre", ""),
            "carrosserie": vehicle_override.get("carrosserie", ""),
            "energie": vehicle_override.get("energie", ""),
            "cylindree": vehicle_override.get("cylindree"),
            "puissance_fiscale": vehicle_override.get("puissance_fiscale"),
            "puissance_kw": float(vehicle_override["puissance_kw"]) if vehicle_override.get("puissance_kw") else None,
            "co2": vehicle_override.get("co2"),
            "nb_places": vehicle_override.get("nb_places"),
            "poids_vide": vehicle_override.get("poids_vide"),
            "ptac": vehicle_override.get("ptac"),
        }
    else:
        vehicle_data = {"sources": [], "marque": "", "genre": "VP"}

    # 5. Cross-validation
    genre = vehicle_data.get("genre", "VP")
    validation = validate_dossier(
        documents_extraits,
        genre_vehicule=genre,
        vehicle_found_in_db="types_mines" in vehicle_data.get("sources", []),
        vehicle_data=vehicle_data,
    )

    if not validation.is_valid:
        update_dossier_status(dossier_id, "documents_manquants")
        update_dossier_data(
            dossier_id,
            immatriculation=cession_data.get("immatriculation", ""),
            vin=cession_data.get("vin", ""),
            donnees_extraites=documents_extraits,
        )
        return {
            "dossier_id": dossier_id,
            "reference": reference,
            "status": "documents_manquants",
            "validation": validation.to_dict(),
        }

    # 6. Calcul taxes
    justif_data = documents_extraits.get("justificatif_domicile", {})
    from src.taxes.region_detector import detect_region
    code_postal = justif_data.get("adresse_code_postal", "")
    region = detect_region(code_postal)

    taxes = calculer_taxes(
        puissance_fiscale=int(vehicle_data.get("puissance_fiscale") or 0),
        region=region,
        energie=vehicle_data.get("energie", ""),
        co2=int(vehicle_data.get("co2") or 0),
        masse=int(vehicle_data.get("poids_vide") or 0),
        genre=genre,
        est_neuf=False,
    )

    # 7. Pré-remplissage CERFA
    cni_data = documents_extraits.get("cni", {})

    demandeur = {
        "nom": cni_data.get("nom", ""),
        "prenom": cni_data.get("prenom", ""),
        "sexe": cni_data.get("sexe", ""),
        "date_naissance": cni_data.get("date_naissance", ""),
        "lieu_naissance": cni_data.get("lieu_naissance", ""),
        "lieu_naissance_departement": cni_data.get("lieu_naissance_departement", ""),
        "adresse_numero": justif_data.get("adresse_numero", ""),
        "adresse_type_voie": justif_data.get("adresse_type_voie", ""),
        "adresse_nom_voie": justif_data.get("adresse_nom_voie", ""),
        "adresse_complete": justif_data.get("adresse_complete", ""),
        "adresse_code_postal": justif_data.get("adresse_code_postal", ""),
        "adresse_ville": justif_data.get("adresse_ville", ""),
        "date_cession": cession_data.get("date_cession", ""),
    }

    # Ajouter les infos de la carte grise vendeur au vehicule (VIN, immat, dates)
    cg_vendeur = documents_extraits.get("carte_grise_vendeur", {})
    vehicle_data["vin"] = cession_data.get("vin", "") or cg_vendeur.get("E_vin", "")
    vehicle_data["immatriculation"] = cession_data.get("immatriculation", "") or cg_vendeur.get("A_immatriculation", "")
    vehicle_data["date_cession"] = cession_data.get("date_cession", "")
    vehicle_data["date_premiere_immat"] = cg_vendeur.get("B_date_premiere_immat", "")
    vehicle_data["date_certificat_actuel"] = cg_vendeur.get("I_date_immatriculation", "")

    cerfa_path = fill_cerfa_from_dossier(demandeur, vehicle_data, taxes)

    # 8. Mettre à jour le dossier
    immat = cession_data.get("immatriculation", "")
    vin = cession_data.get("vin", "")

    # Nom du client = acheteur (cession) ou titulaire (CNI)
    client_nom = ""
    if cession_data.get("acheteur_nom"):
        client_nom = f"{cession_data.get('acheteur_nom', '')} {cession_data.get('acheteur_prenom', '')}".strip()
    elif cni_data.get("nom"):
        client_nom = f"{cni_data.get('nom', '')} {cni_data.get('prenom', '')}".strip()

    update_dossier_status(dossier_id, "pret")
    update_dossier_data(
        dossier_id,
        immatriculation=immat,
        vin=vin,
        donnees_extraites=documents_extraits,
        taxes=taxes,
        cerfa_path=cerfa_path,
    )

    # Sauvegarder le nom du client
    if client_nom:
        engine = _get_engine()
        with engine.connect() as conn:
            conn.execute(
                text("UPDATE dossiers SET client_nom = :nom WHERE id = :id"),
                {"nom": client_nom, "id": dossier_id},
            )
            conn.commit()

    return {
        "dossier_id": dossier_id,
        "reference": reference,
        "status": "pret",
        "immatriculation": immat,
        "vehicule": {
            "marque": vehicle_data.get("marque", ""),
            "denomination": vehicle_data.get("denomination_commerciale", ""),
            "genre": genre,
        },
        "taxes": taxes,
        "cerfa_path": cerfa_path,
        "validation": validation.to_dict(),
    }
