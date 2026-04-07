"""
Router documents — upload avec OCR temps reel.

POST   /documents/{dossier_id}/upload     Uploader un document (vendeur ou client)
GET    /documents/{document_id}           Detail + resultat extraction
"""
from __future__ import annotations

import logging
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException, UploadFile
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.models.base import get_db
from api.models.document import DocumentDB
from api.models.dossier import DossierDB
from storage.document_store import get_document_store

# Import du moteur metier (extrait du demo_server)
from engine.pipeline.realtime import (
    _ocr_google_docai,
    classify_document,
    extract_data,
    _auto_detect_dossier_type,
    _auto_extract_dossier_fields,
    _auto_extract_client_fields,
    _check_pro_docs,
    _check_client_docs,
    _build_recap_validation,
    set_profil_pro,
)
from integrations.llm.claude_extractor import claude_classify, claude_extract, claude_verify
from notifications.messages import DOC_ILLISIBLE, QUALITE_OCR

logger = logging.getLogger(__name__)

router = APIRouter()


# ─── Detection de completude recto/verso ────────────────────────────────────
# Pour chaque type recto/verso, on definit les champs typiques de chaque face.
# Apres extraction, on regarde quels champs sont remplis pour determiner
# quelles faces ont ete deposees et si le document est complet.

FACE_FIELDS: dict[str, dict] = {
    "CNI": {
        "recto": ["nom_naissance", "prenoms", "date_naissance", "lieu_naissance", "sexe"],
        "verso": ["date_expiration", "n_document", "numero_document"],
        # Champs minimum pour considerer le document exploitable
        "required": ["nom_naissance", "date_naissance", "date_expiration"],
    },
    "PASSEPORT": {
        "recto": ["nom_naissance", "prenoms", "date_naissance", "lieu_naissance", "sexe",
                   "date_expiration", "n_document", "numero_document", "mrz_nom"],
        "verso": [],  # Passeport = page unique (photo + MRZ sur meme page)
        "required": ["nom_naissance", "date_naissance", "date_expiration"],
    },
    "PERMIS": {
        "recto": ["nom", "prenom", "date_naissance", "categories", "numero_permis"],
        "verso": ["categories_dates"],
        # Le recto suffit pour le Cerfa (categories)
        "required": ["date_naissance", "categories"],
    },
}


def _analyze_document_faces(doc_type: str, extracted: dict) -> dict | None:
    """
    Analyse les champs extraits pour determiner quelles faces sont presentes.

    Retourne None pour les documents qui ne sont pas recto/verso.
    Pour les recto/verso, retourne :
    {
        "recto_verso": True,
        "recto_present": True/False,
        "verso_present": True/False,
        "complet": True/False,
        "champs_presents": [...],
        "champs_manquants": [...],
        "message": "..."
    }
    """
    fields = FACE_FIELDS.get(doc_type)
    if not fields:
        return None

    # Pas de verso pour le passeport → un seul upload suffit
    if not fields["verso"]:
        required_ok = all(
            _has_field(extracted, f) for f in fields["required"]
        )
        return {
            "recto_verso": False,
            "complet": required_ok,
            "champs_presents": [f for f in fields["recto"] if _has_field(extracted, f)],
            "champs_manquants": [f for f in fields["required"] if not _has_field(extracted, f)],
            "message": None if required_ok else "Des informations essentielles n'ont pas pu etre lues. Re-deposez le document.",
        }

    # Compter les champs de chaque face
    recto_found = sum(1 for f in fields["recto"] if _has_field(extracted, f))
    verso_found = sum(1 for f in fields["verso"] if _has_field(extracted, f))

    recto_present = recto_found >= 2  # Au moins 2 champs recto
    verso_present = verso_found >= 1  # Au moins 1 champ verso

    # Verifier les champs requis
    required_ok = all(_has_field(extracted, f) for f in fields["required"])
    complet = required_ok

    # Message adapte
    if complet:
        message = "Document complet — toutes les informations ont ete extraites."
    elif recto_present and not verso_present:
        message = "Une seule face detectee. Deposez l'autre face du document pour completer."
    elif verso_present and not recto_present:
        message = "Une seule face detectee. Deposez l'autre face du document pour completer."
    else:
        missing = [f for f in fields["required"] if not _has_field(extracted, f)]
        message = f"Informations manquantes : {', '.join(missing)}. Deposez l'autre face ou re-deposez le document."

    return {
        "recto_verso": True,
        "recto_present": recto_present,
        "verso_present": verso_present,
        "complet": complet,
        "champs_presents": (
            [f for f in fields["recto"] if _has_field(extracted, f)]
            + [f for f in fields["verso"] if _has_field(extracted, f)]
        ),
        "champs_manquants": [f for f in fields["required"] if not _has_field(extracted, f)],
        "message": message,
    }


def _has_field(data: dict, field_name: str) -> bool:
    """Verifie si un champ est present et non vide dans les donnees extraites."""
    val = data.get(field_name)
    if val is None:
        return False
    if isinstance(val, str) and not val.strip():
        return False
    if isinstance(val, list) and len(val) == 0:
        return False
    return True


import re as _re

# Puissance max continue par categorie L (reglementation EU 168/2013)
_CATEGORY_MAX_POWER_KW: dict[str, float] = {
    "L1e": 4, "L1e-A": 0.25, "L1e-B": 4,
    "L2e": 4,
    "L3e-A1": 11, "L3e-A1E": 11,
    "L3e-A2": 35, "L3e-A2E": 35,
    "L3e-A3": 999, "L3e-A3E": 999,
    "L4e-A1": 11, "L4e-A2": 35, "L4e-A3": 999,
    "L5e": 15,
    "L6e": 6, "L7e": 15,
}


def _postprocess_coc(extracted: dict, ocr_text: str) -> None:
    """
    Post-validation du COC : corrige les erreurs d'extraction courantes.

    Probleme typique : l'OCR melange les colonnes du COC, et Claude confond
    la vitesse max (champ 1.8) avec la puissance (champ 3.3.3.4).
    On valide la puissance extraite vs la categorie du vehicule et on
    tente une correction par regex si incoherent.
    """
    cat = (extracted.get("categorie_j") or "").upper()
    puissance = extracted.get("puissance_kw")
    energie = (extracted.get("energie") or "").lower()

    # Trouver la puissance max reglementaire pour cette categorie
    max_kw = None
    for cat_prefix, limit in _CATEGORY_MAX_POWER_KW.items():
        if cat.startswith(cat_prefix.upper()):
            max_kw = limit
            break

    # Si puissance extraite depasse la limite reglementaire de la categorie → fausse
    # Tenter de corriger en cherchant le bon nombre dans le texte OCR
    if puissance and max_kw and puissance > max_kw:
        logger.warning(
            f"[COC PostProcess] puissance_kw={puissance} depasse la limite "
            f"categorie {cat} (max {max_kw} kW) — tentative de correction"
        )

        # Strategie 1 : chercher un nombre apres "Maximum 30 minutes power" ou "Maximum net power"
        m = _re.search(
            r"[Mm]aximum\s*(?:30\s*minutes\s*|net\s*)?power[^:]*:[^\d]*(\d+(?:\.\d+)?)",
            ocr_text, _re.DOTALL
        )
        if m:
            val = float(m.group(1))
            after = ocr_text[m.end(1):m.end(1)+5]
            if not _re.match(r"\.\d", after) and val <= max_kw and val > 0:
                extracted["puissance_kw"] = val
                logger.info(f"[COC PostProcess] puissance corrigee → {val} kW (regex apres label)")
                return

        # Strategie 2 : chercher un nombre entier isole sur sa propre ligne,
        # le plus proche du mot "electric" ou "kW" dans le texte OCR
        # (le layout colonne melange souvent la valeur loin du label)
        best = None
        best_dist = float("inf")
        for m in _re.finditer(r"\n(\d{1,3})\n", ocr_text):
            val = int(m.group(1))
            if val <= 0 or val > max_kw:
                continue
            for em in _re.finditer(r"electric|kW|power", ocr_text, _re.IGNORECASE):
                dist = abs(m.start() - em.start())
                if dist < best_dist:
                    best_dist = dist
                    best = val
        if best:
            extracted["puissance_kw"] = best
            logger.info(f"[COC PostProcess] puissance corrigee → {best} kW (nombre isole proche de 'electric/kW')")
            return

        # Aucune correction trouvee — garder null plutot qu'une valeur fausse
        extracted["puissance_kw"] = None
        logger.warning(f"[COC PostProcess] puissance mise a null — valeur non trouvable dans le texte")

    # Corriger modele : "VARG 1" est le "Type" (0.2), pas le nom commercial
    # Le nom commercial est dans le champ 0.2.3 mais l'OCR le separe de son label
    # Chercher le nom commercial dans le texte : ligne isolee en majuscules entre les champs
    modele = extracted.get("modele", "")
    if modele and _re.match(r"^[A-Z]+ \d+$", modele):
        # Chercher "VARG" (ou similaire) comme ligne isolee dans le texte
        m = _re.search(r"Commercial\s*name.*?\n.*?\n([A-Z][A-Za-z0-9]{2,20})\n", ocr_text, _re.DOTALL)
        if m:
            extracted["modele"] = m.group(1).strip()

ALLOWED_MIME_TYPES = {
    "application/pdf",
    "image/jpeg",
    "image/png",
    "image/tiff",
    "image/webp",
}
MAX_FILE_SIZE = 10 * 1024 * 1024


@router.post("/{dossier_id}/upload", status_code=201)
async def upload_document(
    dossier_id: UUID,
    file: UploadFile,
    source: str = "vendeur",
    captured_by_camera: bool = False,
    doc_type: str | None = None,
    db: AsyncSession = Depends(get_db),
):
    """
    Upload un document — OCR + classification + extraction en temps reel.

    Le moteur complet du demo_server est utilise :
    - OCR Google Document AI
    - Classification automatique du type de document
    - Extraction des donnees
    - Detection auto VN/VO (si vendeur)
    - Mise a jour checklist
    """
    dossier = await db.get(DossierDB, dossier_id)
    if not dossier:
        raise HTTPException(status_code=404, detail="Dossier non trouve")

    # Filtrer les fichiers systeme (#12)
    fname = file.filename or ""
    if fname.startswith(".") or fname in (".DS_Store", "Thumbs.db", "desktop.ini"):
        raise HTTPException(status_code=422, detail=f"Fichier systeme ignore : {fname}")

    # Verifications client (#9-11)
    metadata = dossier.metadata_ or {}
    if source == "client":
        if not metadata.get("client_rgpd_consent"):
            raise HTTPException(403, detail={
                "error": "consentement_requis",
                "message": "Vous devez accepter les conditions de traitement de vos donnees avant de deposer vos documents.",
            })
        if not metadata.get("cpi_mode"):
            raise HTTPException(403, detail={
                "error": "choix_cpi_requis",
                "message": "Choisissez d'abord comment vous souhaitez recevoir votre CPI.",
            })
        if metadata.get("cession_signee_client") and not metadata.get("cession_client_telechargee"):
            raise HTTPException(403, detail={
                "error": "telechargement_cession_requis",
                "message": "Vous devez telecharger votre exemplaire du certificat de cession avant de pouvoir continuer.",
            })

    if file.content_type not in ALLOWED_MIME_TYPES:
        raise HTTPException(status_code=422, detail=f"Type de fichier non supporte : {file.content_type}")

    file_bytes = await file.read()
    if len(file_bytes) > MAX_FILE_SIZE:
        raise HTTPException(status_code=422, detail="Fichier trop volumineux (max 10 MB)")
    if len(file_bytes) == 0:
        raise HTTPException(status_code=422, detail="Fichier vide")

    # Stocker le fichier
    store = get_document_store()
    sha256 = store.compute_sha256(file_bytes)
    doc_id = uuid4()
    storage_path = f"{dossier_id}/{doc_id}/{file.filename}"
    await store.save(file_bytes, storage_path, file.content_type)

    # Creer en BDD
    document = DocumentDB(
        id=doc_id,
        dossier_id=dossier_id,
        source=source,
        type="PENDING",
        status="PENDING",
        captured_by_camera=captured_by_camera,
        storage_path=storage_path,
        original_filename=file.filename or "unknown",
        mime_type=file.content_type,
        file_size_bytes=len(file_bytes),
        sha256=sha256,
    )
    db.add(document)
    await db.flush()

    # ═══════════════════════════════════════════════════════════════════
    # PIPELINE : Google DocAI (OCR) → Claude Opus (extraction)
    #
    # Google DocAI : lit le texte brut des images/PDF
    # Claude Opus : comprend le texte, extrait les champs en JSON
    # Python : valide le JSON, verifie la coherence
    # ═══════════════════════════════════════════════════════════════════

    mime = file.content_type or ""
    raw_text = ""
    ocr_confidence = 0.0
    ocr_provider_used = "none"

    OCR_SEUIL_ILLISIBLE = 0.40
    OCR_SEUIL_AVERTISSEMENT = 0.70

    # Etape 1 : Google DocAI (OCR — lecture du texte brut)
    if mime in ALLOWED_MIME_TYPES:
        try:
            goo = _ocr_google_docai(file_bytes, mime)
            raw_text = goo["text"]
            ocr_confidence = goo["confidence"]
            ocr_provider_used = "google_docai"
            logger.info(f"[OCR] Google DocAI: {ocr_confidence:.0%}, {len(raw_text)} chars")
        except Exception as e:
            logger.error(f"[OCR] Google DocAI echoue: {e}")

    # ─── Qualite (basee sur la confidence Google DocAI) ───
    via_fichier = not captured_by_camera
    if ocr_confidence < OCR_SEUIL_ILLISIBLE:
        quality_status = "illisible"
        if via_fichier:
            quality_message = DOC_ILLISIBLE["fichier_1ere_tentative"]
        else:
            quality_message = DOC_ILLISIBLE["photo_1ere_tentative"]
    elif ocr_confidence < OCR_SEUIL_AVERTISSEMENT:
        quality_status = "avertissement"
        quality_message = QUALITE_OCR["avertissement"]
    else:
        quality_status = "ok"
        quality_message = "Document bien recu et lisible."

    # ─── Etape 2 : Claude Opus (classification + extraction) ───
    detected_type = "PENDING"
    cls_confidence = 0.0
    keywords: list[str] = []
    extracted: dict = {}

    if quality_status != "illisible" and raw_text.strip():
        # Si doc_type est fourni (ex: client qui depose dans un emplacement specifique), on le force
        if doc_type and doc_type not in ("PENDING", "AUTRE"):
            detected_type = doc_type
            cls_confidence = 1.0
            logger.info(f"[Upload] Type force par le client: {detected_type}")
        else:
            # Classification via Claude Opus
            try:
                claude_cls = await claude_classify(raw_text)
                detected_type = claude_cls.get("type", "AUTRE")
                cls_confidence = claude_cls.get("confidence", 0.0)
                logger.info(f"[Claude] Classification: {detected_type} ({cls_confidence:.0%})")
            except Exception as e:
                logger.warning(f"[Claude] Classification echouee, fallback regex: {e}")
                detected_type, cls_confidence, keywords = classify_document(raw_text)

        # Extraction via Claude Opus
        if detected_type and detected_type not in ("AUTRE", "PENDING"):
            try:
                extracted = await claude_extract(detected_type, raw_text)
                logger.info(f"[Claude] Extraction {detected_type}: {len(extracted)} champs")
            except Exception as e:
                logger.warning(f"[Claude] Extraction echouee, fallback regex: {e}")
                extracted = extract_data(detected_type, raw_text)
        else:
            # Fallback regex pour les types non reconnus
            extracted = extract_data(detected_type, raw_text)

    # ─── Post-validation COC : corriger puissance electrique ───
    if detected_type == "COC" and extracted:
        _postprocess_coc(extracted, raw_text)

    # ─── Post-validation CG : verifier si barree ───
    cg_non_barree = False
    if detected_type == "CG_BARREE" and extracted:
        barre = extracted.get("barre_diagonale")
        if barre is False or (barre is None and not extracted.get("date_vente")):
            cg_non_barree = True
            # On garde le document pour que le vendeur voie le message,
            # mais on le marque comme problematique
            extracted["_cg_non_barree"] = True

    doc_status = "REJECTED" if quality_status == "illisible" else "EXTRACTED"

    # ─── Anti-doublon / fusion recto-verso (#14) ───
    # Types qui ont un recto/verso
    RECTO_VERSO_TYPES = {"CNI", "PASSEPORT", "PERMIS"}

    # Cas 1 : meme type deja present → fusion recto/verso
    if detected_type != "AUTRE" and detected_type != "PENDING":
        existing = await db.execute(
            select(DocumentDB).where(
                DocumentDB.dossier_id == dossier_id,
                DocumentDB.source == source,
                DocumentDB.type == detected_type,
                DocumentDB.id != doc_id,
            )
        )
        existing_doc = existing.scalar_one_or_none()
        if existing_doc:
            merged_text = (existing_doc.ocr_raw_text or "") + "\n" + raw_text
            # Re-extraire avec Claude Opus sur le texte fusionne
            try:
                merged_extracted = await claude_extract(detected_type, merged_text)
            except Exception:
                merged_extracted = extract_data(detected_type, merged_text)
            for k, v in merged_extracted.items():
                if v and not extracted.get(k):
                    extracted[k] = v
            raw_text = merged_text
            await db.delete(existing_doc)
            logger.info(f"[Fusion recto/verso] {detected_type} : {existing_doc.original_filename} + {file.filename}")

    # Cas 2 : verso non reconnu (AUTRE/PENDING) mais un recto existe → forcer la fusion
    elif detected_type in ("AUTRE", "PENDING"):
        for rv_type in RECTO_VERSO_TYPES:
            existing = await db.execute(
                select(DocumentDB).where(
                    DocumentDB.dossier_id == dossier_id,
                    DocumentDB.source == source,
                    DocumentDB.type == rv_type,
                    DocumentDB.id != doc_id,
                )
            )
            existing_doc = existing.scalar_one_or_none()
            if existing_doc:
                # On a un recto de ce type → ce fichier est probablement le verso
                detected_type = rv_type
                merged_text = (existing_doc.ocr_raw_text or "") + "\n" + raw_text
                try:
                    merged_extracted = await claude_extract(detected_type, merged_text)
                except Exception:
                    merged_extracted = extract_data(detected_type, merged_text)
                for k, v in merged_extracted.items():
                    if v and not extracted.get(k):
                        extracted[k] = v
                raw_text = merged_text
                await db.delete(existing_doc)
                logger.info(f"[Fusion verso auto] {detected_type} : {existing_doc.original_filename} + {file.filename}")
                break

    # MAJ document BDD
    document.type = detected_type
    document.status = doc_status
    document.ocr_provider = ocr_provider_used
    document.ocr_confidence = ocr_confidence
    document.ocr_raw_text = raw_text[:5000] if raw_text else None
    document.extracted_data = extracted
    document.auto_classified = cls_confidence >= 0.60
    document.classification_confidence = cls_confidence

    await db.flush()

    # ─── Si upload vendeur : detection auto VN/VO + extraction infos dossier ───
    dossier_dict = None
    checklist = None

    if source == "vendeur":
        # Construire un dossier dict compatible avec le moteur
        dossier_dict = await _build_dossier_dict(db, dossier)

        _auto_detect_dossier_type(dossier_dict)
        _auto_extract_dossier_fields(dossier_dict)

        # Mettre a jour le dossier BDD
        if dossier_dict.get("type") and not dossier.type:
            dossier.type = dossier_dict["type"]
            # Tarification automatique : 12 EUR moto, 14 EUR voiture
            detected_upper = dossier_dict["type"].upper()
            is_moto = detected_upper in ("MOTO", "L1E", "L2E", "L3E", "L4E", "L5E", "L6E", "L7E")
            dossier.montant_honoraires = 12.0 if is_moto else 14.0
        if dossier_dict.get("vin") and not dossier.vin:
            dossier.vin = dossier_dict["vin"]
        if dossier_dict.get("immatriculation") and not dossier.immatriculation:
            dossier.immatriculation = dossier_dict["immatriculation"]
        if dossier_dict.get("client_nom") and not dossier.client_nom:
            dossier.client_nom = dossier_dict["client_nom"]
        if dossier_dict.get("client_prenom") and not dossier.client_prenom:
            dossier.client_prenom = dossier_dict["client_prenom"]

        await db.flush()

        # Checklist vendeur
        checklist = _check_pro_docs(dossier_dict)

        # Recapitulatif si tout est pret
        recap = None
        if checklist.get("client_link_ready"):
            recap = _build_recap_validation(dossier_dict)

    elif source == "client":
        # Post-traitement client (#16-17)
        dossier_dict = await _build_dossier_dict(db, dossier)
        _auto_extract_client_fields(dossier_dict)

        # Mettre a jour dossier BDD depuis extraction client
        if dossier_dict.get("client_sexe") and not (metadata.get("client_sexe")):
            metadata["client_sexe"] = dossier_dict["client_sexe"]
            dossier.metadata_ = metadata
            from sqlalchemy.orm.attributes import flag_modified
            flag_modified(dossier, 'metadata_')
        if dossier_dict.get("client_nom"):
            dossier.client_nom = dossier_dict["client_nom"]
        if dossier_dict.get("client_prenom"):
            dossier.client_prenom = dossier_dict["client_prenom"]
        if dossier_dict.get("is_personne_morale"):
            dossier.is_personne_morale = True

        await db.flush()
        checklist = _check_client_docs(dossier_dict)

    # ─── Detection de completude du dossier ───
    dossier_complet = False
    completude_message = None
    docs_manquants = []

    if checklist:
        if source == "vendeur":
            dossier_complet = checklist.get("all_ok", False)
            docs_manquants = [
                m.get("label", m.get("id", "?"))
                for m in checklist.get("blocages", [])
                if m.get("status") == "manquant"
            ]
            if dossier_complet:
                completude_message = (
                    "Nickel, tous les documents vehicule sont la ! "
                    "Vous pouvez deposer les documents client ou envoyer un lien SMS a votre client."
                )
            elif docs_manquants:
                completude_message = (
                    f"Bien recu ! Il manque encore : {', '.join(docs_manquants)}. "
                    f"Un petit ajustement et on est bons !"
                )
        elif source == "client":
            dossier_complet = checklist.get("ready_for_diagnostic", False)
            docs_manquants = [
                m.get("label", m.get("type", "?"))
                for m in checklist.get("missing", [])
                if m.get("required")
            ]
            if dossier_complet:
                completude_message = (
                    "Parfait, tous vos documents sont bien recus ! "
                    "Plus qu'a confirmer l'envoi et c'est termine."
                )
            elif docs_manquants:
                completude_message = (
                    f"Bien recu ! Il manque encore : {', '.join(docs_manquants)}. "
                    f"Ca prend 2 minutes."
                )

    # ─── Verification inter-documents (quand le dossier client est complet) ───
    coherence_warnings: list[dict] = []
    if source == "client" and dossier_complet and dossier_dict:
        try:
            coherence_warnings = await _verify_cross_documents(dossier_dict)
        except Exception as e:
            logger.warning(f"[Verify] Coherence inter-docs echouee: {e}")

    # ─── Analyse faces recto/verso ───
    faces_info = _analyze_document_faces(detected_type, extracted)

    # ─── Info CNIT manquant (COC europeen) ───
    cnit_info = None
    if detected_type == "COC" and source == "vendeur" and not extracted.get("cnit"):
        cnit_info = {
            "cnit_absent": True,
            "message": (
                "Le CNIT (type mines, champ D.2.1) n'a pas ete trouve sur ce COC — "
                "c'est normal pour un COC europeen. "
                "Vous pourrez saisir le CNIT manuellement avant de generer le Cerfa. "
                "Le Cerfa sera mis a jour numeriquement, sans impression ni ajout manuscrit."
            ),
        }

    # ─── Alerte CG non barree ───
    cg_alerte = None
    if cg_non_barree:
        cg_alerte = {
            "cg_non_barree": True,
            "message": (
                "Cette carte grise n'est pas barree. "
                "Pour une vente de vehicule d'occasion, la carte grise doit comporter : "
                "une barre diagonale, la mention \"vendu le\" ou \"cede le\" suivie "
                "de la date et de l'heure de la vente, ainsi que le nom et prenom "
                "de l'acheteur ecrits a la main sur ou pres de la barre. "
                "Veuillez deposer la carte grise correctement barree."
            ),
        }

    return {
        "document_id": str(doc_id),
        "dossier_id": str(dossier_id),
        "type": detected_type,
        "status": doc_status,
        "filename": file.filename,
        "size_bytes": len(file_bytes),
        "quality": {
            "status": quality_status,
            "ocr_confidence": ocr_confidence,
            "ocr_provider": ocr_provider_used,
            "message": quality_message,
            "problems": [{"message": quality_message}] if quality_message else [],
        },
        "extracted_fields": extracted,
        "classification": {
            "type": detected_type,
            "confidence": cls_confidence,
            "keywords": keywords,
        },
        "faces": faces_info,
        "cnit_info": cnit_info,
        "cg_alerte": cg_alerte,
        "dossier_complet": dossier_complet,
        "completude": {
            "complet": dossier_complet,
            "message": completude_message,
            "docs_manquants": docs_manquants,
        },
        "pro_docs_checklist": checklist if source == "vendeur" else None,
        "client_docs_checklist": checklist if source == "client" else None,
        "recapitulatif_validation": recap if source == "vendeur" and checklist and checklist.get("client_link_ready") else None,
        "coherence_warnings": coherence_warnings if coherence_warnings else None,
    }


@router.get("/{document_id}")
async def get_document(
    document_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    doc = await db.get(DocumentDB, document_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document non trouve")

    faces_info = _analyze_document_faces(doc.type, doc.extracted_data or {})

    return {
        "id": str(doc.id),
        "dossier_id": str(doc.dossier_id),
        "type": doc.type,
        "status": doc.status,
        "source": doc.source,
        "filename": doc.original_filename,
        "ocr_confidence": doc.ocr_confidence,
        "ocr_provider": doc.ocr_provider,
        "extracted_data": doc.extracted_data,
        "faces": faces_info,
        "auto_classified": doc.auto_classified,
        "classification_confidence": doc.classification_confidence,
        "created_at": doc.created_at.isoformat() if doc.created_at else None,
    }


# ─── Helpers ─────────────────────────────────────────────────────────────────

async def _sync_profil_pro(db: AsyncSession, professionnel_id) -> None:
    """Peuple PROFIL_PRO dans realtime.py depuis la BDD."""
    from api.models.professionnel import Professionnel
    pro = await db.get(Professionnel, professionnel_id)
    if pro:
        set_profil_pro({
            "nom_commerce": pro.nom_commerce,
            "adresse": pro.adresse,
            "telephone_commerce": pro.telephone_commerce,
            "email_commerce": pro.email_commerce,
            "cachet_path": pro.cachet_path,
            "signature_path": pro.signature_path,
            "kbis_path": pro.kbis_path,
            "siret": pro.siret,
            "raison_sociale": pro.raison_sociale,
            "assurance_flotte_vn": pro.assurance_flotte_vn,
            "assurance_flotte_vo": pro.assurance_flotte_vo,
            "demander_assurance_client_vn": pro.demander_assurance_client_vn,
            "demander_assurance_client_vo": pro.demander_assurance_client_vo,
        })


async def _build_dossier_dict(db: AsyncSession, dossier: DossierDB) -> dict:
    """
    Construit un dict compatible avec le moteur realtime depuis le dossier BDD.
    Le moteur du demo_server travaille sur des dicts — c'est le pont.
    Peuple aussi PROFIL_PRO automatiquement.
    """
    # Peupler PROFIL_PRO depuis la BDD
    await _sync_profil_pro(db, dossier.professionnel_id)

    # Charger les documents
    result = await db.execute(
        select(DocumentDB).where(DocumentDB.dossier_id == dossier.id)
    )
    docs = result.scalars().all()

    docs_vendeur = []
    docs_client = []

    for doc in docs:
        d = {
            "id": str(doc.id),
            "type": doc.type or "PENDING",
            "filename": doc.original_filename,
            "storage_path": doc.storage_path,
            "source": doc.source,
            "status": doc.status,
            "extracted_data": doc.extracted_data or {},
            "ocr_confidence": doc.ocr_confidence,
            "captured_by_camera": doc.captured_by_camera,
            "quality": {
                "status": "ok" if doc.status == "EXTRACTED" else "illisible" if doc.status == "REJECTED" else "en_cours",
                "confidence": doc.ocr_confidence,
            },
        }
        if doc.source == "client":
            docs_client.append(d)
        else:
            docs_vendeur.append(d)

    return {
        "id": str(dossier.id),
        "type": dossier.type,
        "client_telephone": dossier.client_telephone,
        "client_email": dossier.client_email,
        "client_nom": dossier.client_nom,
        "client_prenom": dossier.client_prenom,
        "client_sexe": None,
        "vin": dossier.vin,
        "immatriculation": dossier.immatriculation,
        "is_personne_morale": dossier.is_personne_morale,
        "documents_vendeur": docs_vendeur,
        "documents_client": docs_client,
        "documents": docs_vendeur + docs_client,
        "status": dossier.status,
        # Metadata
        "pas_de_certificat_cession": (dossier.metadata_ or {}).get("pas_de_certificat_cession", False),
        "demander_assurance_client": (dossier.metadata_ or {}).get("demander_assurance_client", False),
        "assurance_flotte_couvre": (dossier.metadata_ or {}).get("assurance_flotte_couvre", False),
        "choix_assurance_pro": (dossier.metadata_ or {}).get("choix_assurance_pro"),
    }


async def _verify_cross_documents(dossier_dict: dict) -> list[dict]:
    """
    Verifie la coherence inter-documents quand le dossier client est complet.
    Compare : CNI/passeport vs CG (nom), CNI vs permis (nom + date naissance),
    facture/CG vs COC (VIN).
    """
    warnings: list[dict] = []
    all_docs = dossier_dict.get("documents", [])

    # Indexer par type
    by_type: dict[str, dict] = {}
    for doc in all_docs:
        t = doc.get("type")
        if t and doc.get("extracted_data"):
            by_type[t] = doc["extracted_data"]

    # Identite : CNI ou PASSEPORT vs CG_BARREE (nom titulaire)
    id_doc = by_type.get("CNI") or by_type.get("PASSEPORT")
    cg_doc = by_type.get("CG_BARREE")
    if id_doc and cg_doc:
        try:
            result = await claude_verify(id_doc, cg_doc, "identite_vs_cg")
            if not result.get("coherent"):
                warnings.append({
                    "check": "identite_vs_cg",
                    "coherent": False,
                    "details": result.get("details", ""),
                    "problemes": result.get("problemes", []),
                })
        except Exception as e:
            logger.warning(f"[Verify] identite_vs_cg echoue: {e}")

    # Vehicule : COC vs CG_BARREE ou FACTURE (VIN)
    coc_doc = by_type.get("COC")
    facture_doc = by_type.get("FACTURE")
    vehicle_ref = coc_doc or facture_doc
    if vehicle_ref and cg_doc:
        try:
            result = await claude_verify(vehicle_ref, cg_doc, "vehicule_vin")
            if not result.get("coherent"):
                warnings.append({
                    "check": "vehicule_vin",
                    "coherent": False,
                    "details": result.get("details", ""),
                    "problemes": result.get("problemes", []),
                })
        except Exception as e:
            logger.warning(f"[Verify] vehicule_vin echoue: {e}")

    return warnings
