"""
Router documents — version locale d'Imatra.

POST   /documents/{dossier_id}/upload     Uploader un document (depuis fichier local)
GET    /documents/{document_id}           Détail + résultat d'extraction

L'upload appelle le pipeline OCR local (PaddleOCR via la factory)
puis classifie et extrait les données du document.

Le drag & drop d'emails (Phase 4) sera ajouté dans un router séparé
qui appellera ce même endpoint en boucle pour chaque pièce jointe.
"""
from __future__ import annotations

import logging
import uuid

from fastapi import APIRouter, Depends, HTTPException, UploadFile
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.models.base import get_db
from api.models.document import DocumentDB
from api.models.dossier import DossierDB
from storage.document_store import get_document_store

# Pipeline métier
from engine.pipeline.realtime import (
    classify_document,
    extract_data,
    _auto_detect_dossier_type,
    _auto_extract_dossier_fields,
    _auto_extract_client_fields,
    _check_pro_docs,
    _check_client_docs,
    set_profil_pro,
)

logger = logging.getLogger(__name__)

router = APIRouter()


# ─── Configuration ──────────────────────────────────────────────────────────

ALLOWED_MIME_TYPES = {
    "application/pdf",
    "image/jpeg",
    "image/png",
    "image/tiff",
    "image/webp",
}
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB

OCR_SEUIL_ILLISIBLE = 0.40
OCR_SEUIL_AVERTISSEMENT = 0.70


# ─── Endpoint upload ────────────────────────────────────────────────────────


@router.post("/{dossier_id}/upload", status_code=201)
async def upload_document(
    dossier_id: str,
    file: UploadFile,
    doc_type: str | None = None,
    source_email_subject: str | None = None,
    source_email_from: str | None = None,
    db: AsyncSession = Depends(get_db),
):
    """
    Upload un document — OCR + classification + extraction en local.

    L'agent uploade un fichier (depuis son disque ou extrait d'un email).
    Le pipeline tourne intégralement en local via PaddleOCR.
    """
    dossier = await db.get(DossierDB, dossier_id)
    if not dossier:
        raise HTTPException(status_code=404, detail="Dossier non trouvé")

    # Filtrer les fichiers système
    fname = file.filename or ""
    if fname.startswith(".") or fname in (".DS_Store", "Thumbs.db", "desktop.ini"):
        raise HTTPException(status_code=422, detail=f"Fichier système ignoré : {fname}")

    if file.content_type not in ALLOWED_MIME_TYPES:
        raise HTTPException(
            status_code=422,
            detail=f"Type de fichier non supporté : {file.content_type}",
        )

    file_bytes = await file.read()
    if len(file_bytes) > MAX_FILE_SIZE:
        raise HTTPException(status_code=422, detail="Fichier trop volumineux (max 10 MB)")
    if len(file_bytes) == 0:
        raise HTTPException(status_code=422, detail="Fichier vide")

    # Stocker le fichier UNE SEULE FOIS (chiffré local). Si le fichier contient
    # plusieurs documents (PDF multi-pages), on créera N rows en BDD pointant
    # toutes vers ce même storage_path.
    store = get_document_store()
    sha256 = store.compute_sha256(file_bytes)
    upload_id = str(uuid.uuid4())
    storage_path = f"{dossier_id}/{upload_id}/{file.filename}"
    await store.save(file_bytes, storage_path, file.content_type)

    # ════════════════════════════════════════════════════════════════════
    # PIPELINE LOCAL : PaddleOCR (par page) → classification (par page) →
    # groupement → N documents logiques
    # ════════════════════════════════════════════════════════════════════
    ocr_result = None
    ocr_provider_used = "none"
    try:
        from integrations.ocr_providers import get_ocr_provider
        from config.settings import get_settings
        provider = get_ocr_provider(get_settings().ocr_provider)
        ocr_result = await provider.process_document(file_bytes, file.content_type or "")
        ocr_provider_used = ocr_result.provider
        logger.info(
            f"[OCR] {ocr_provider_used}: {ocr_result.average_confidence:.0%}, "
            f"{len(ocr_result.pages)} page(s), {len(ocr_result.full_text)} chars"
        )
    except Exception as e:
        logger.error(f"[OCR] échec : {e}")

    # Découpage en documents logiques. Une page non reconnue est silencieusement
    # ignorée (juste loggée). Cf. décision produit : pas de pop-up "page non reconnue".
    SCORE_MIN_CLASSIF = 0.20
    logical_docs: list[dict] = []  # [{type, text, confidence, page_range, score}]
    if ocr_result and ocr_result.pages:
        # Étape 1 : classifier chaque page
        page_classifs = []
        for page in ocr_result.pages:
            try:
                ptype, pscore, _ = classify_document(page.text)
            except Exception:
                ptype, pscore = "AUTRE", 0.0
            if pscore < SCORE_MIN_CLASSIF:
                logger.info(f"[Classify] page {page.page_number} non reconnue (score {pscore:.2f}) — ignorée")
                ptype = "INCONNU"
            page_classifs.append({"page": page, "type": ptype, "score": pscore})

        # Étape 2 : grouper les pages consécutives de même type (sauf INCONNU)
        i = 0
        while i < len(page_classifs):
            cur = page_classifs[i]
            if cur["type"] == "INCONNU":
                i += 1
                continue
            j = i
            while j + 1 < len(page_classifs) and page_classifs[j + 1]["type"] == cur["type"]:
                j += 1
            group_pages = [page_classifs[k]["page"] for k in range(i, j + 1)]
            text = "\n\n".join(p.text for p in group_pages)
            avg_conf = sum(p.confidence for p in group_pages) / len(group_pages)
            logical_docs.append({
                "type": cur["type"],
                "text": text,
                "confidence": avg_conf,
                "score": cur["score"],
                "page_range": f"{group_pages[0].page_number}-{group_pages[-1].page_number}"
                              if len(group_pages) > 1 else str(group_pages[0].page_number),
                "page_count": len(group_pages),
            })
            i = j + 1

    # Si rien n'a été reconnu, on crée quand même UN document marqué "AUTRE"
    # pour que l'agent puisse le retrouver dans la liste et le classer manuellement.
    if not logical_docs:
        logical_docs = [{
            "type": "AUTRE",
            "text": ocr_result.full_text if ocr_result else "",
            "confidence": ocr_result.average_confidence if ocr_result else 0.0,
            "score": 0.0,
            "page_range": "1",
            "page_count": 1,
        }]

    logger.info(f"[Upload] {len(logical_docs)} document(s) logique(s) détecté(s) dans {file.filename}")

    # Variables compatibilité réponse (premier doc créé)
    raw_text = logical_docs[0]["text"]
    ocr_confidence = logical_docs[0]["confidence"]
    document = None  # sera assigné au premier DocumentDB créé ci-dessous

    created_docs = []
    detected_type = "AUTRE"
    cls_confidence = 0.0
    extracted: dict = {}
    quality_status = "ok"
    quality_message = "Document bien reçu et lisible."

    for idx, ldoc in enumerate(logical_docs):
        ld_text = ldoc["text"]
        ld_conf = ldoc["confidence"]
        ld_type = ldoc["type"]

        # Qualité par doc logique
        if ld_conf < OCR_SEUIL_ILLISIBLE:
            ld_quality = "illisible"
        elif ld_conf < OCR_SEUIL_AVERTISSEMENT:
            ld_quality = "avertissement"
        else:
            ld_quality = "ok"

        # Si l'agent a forcé doc_type au upload, on l'applique uniquement au 1er doc logique
        if idx == 0 and doc_type and doc_type not in ("PENDING", "AUTRE"):
            ld_type = doc_type
            cls_score = 1.0
        else:
            cls_score = ldoc["score"]

        # Extraction si type reconnu
        ld_extracted: dict = {}
        if ld_quality != "illisible" and ld_type not in ("AUTRE", "PENDING") and ld_text.strip():
            try:
                ld_extracted = extract_data(ld_type, ld_text)
            except Exception as e:
                logger.warning(f"[Extract] échec sur {ld_type} : {e}")
        # Métadonnée page_range stockée dans extracted_data
        ld_extracted["__page_range"] = ldoc["page_range"]
        ld_extracted["__page_count"] = ldoc["page_count"]

        ld_doc_id = str(uuid.uuid4())
        new_doc = DocumentDB(
            id=ld_doc_id,
            dossier_id=dossier_id,
            type=ld_type,
            status="REJECTED" if ld_quality == "illisible" else "EXTRACTED",
            storage_path=storage_path,  # Tous les docs logiques partagent le même fichier source
            original_filename=file.filename or "unknown",
            mime_type=file.content_type,
            file_size_bytes=len(file_bytes),
            sha256=sha256,
            source_email_subject=source_email_subject,
            source_email_from=source_email_from,
            ocr_provider=ocr_provider_used,
            ocr_confidence=ld_conf,
            ocr_raw_text=ld_text,
            extracted_data=ld_extracted,
            classification_confidence=cls_score,
            auto_classified=doc_type is None,
        )
        db.add(new_doc)
        created_docs.append(new_doc)
        if document is None:
            document = new_doc
            detected_type = ld_type
            cls_confidence = cls_score
            extracted = ld_extracted
            quality_status = ld_quality

    # Auto-détection VN/VO et extraction des champs du dossier
    # Examen sur l'ensemble des documents logiques créés (et plus seulement le premier)
    all_types = {d.type for d in created_docs}
    if all_types & {"COC", "FACTURE", "CG_BARREE"}:
        dossier_dict = await _build_dossier_dict(db, dossier)
        try:
            # _auto_detect_dossier_type modifie dossier_dict["type"] in place.
            _auto_detect_dossier_type(dossier_dict)
            new_type = dossier_dict.get("type")
            # Toujours réévaluer : si un COC arrive après une CG, le dossier
            # doit basculer de VO → VN.
            if new_type:
                dossier.type = new_type
        except Exception as e:
            logger.warning(f"[AutoDetect] échec : {e}")

        try:
            # Modifie dossier_dict in place ; on lit les champs ensuite.
            _auto_extract_dossier_fields(dossier_dict)
            for k in ("vin", "immatriculation", "client_nom", "client_prenom"):
                v = dossier_dict.get(k)
                if v and hasattr(dossier, k) and not getattr(dossier, k):
                    setattr(dossier, k, v)
        except Exception as e:
            logger.warning(f"[AutoExtract dossier] échec : {e}")

    if all_types & {"CNI", "PASSEPORT", "PERMIS", "DOMICILE"}:
        dossier_dict = await _build_dossier_dict(db, dossier)
        try:
            _auto_extract_client_fields(dossier_dict)
            for k in ("client_nom", "client_prenom", "client_sexe",
                      "is_personne_morale", "siren", "raison_sociale"):
                v = dossier_dict.get(k)
                if v is not None and hasattr(dossier, k) and not getattr(dossier, k):
                    setattr(dossier, k, v)
        except Exception as e:
            logger.warning(f"[AutoExtract client] échec : {e}")

    await db.flush()

    return {
        "document_id": document.id,
        "dossier_id": dossier_id,
        "type": document.type,
        "status": document.status,
        "ocr": {
            "provider": ocr_provider_used,
            "confidence": ocr_confidence,
            "quality": quality_status,
            "message": quality_message,
        },
        "classification": {
            "detected": detected_type,
            "confidence": cls_confidence,
        },
        "extracted": extracted,
        # Si plusieurs documents logiques détectés dans le même fichier
        "logical_documents": [
            {
                "id": d.id,
                "type": d.type,
                "page_range": (d.extracted_data or {}).get("__page_range", "1"),
                "confidence": d.ocr_confidence,
            }
            for d in created_docs
        ],
    }


@router.get("/{document_id}")
async def get_document(document_id: str, db: AsyncSession = Depends(get_db)):
    """Récupère le détail d'un document (métadonnées + extraction)."""
    doc = await db.get(DocumentDB, document_id)
    if not doc:
        raise HTTPException(404, "Document non trouvé")
    return {
        "id": doc.id,
        "dossier_id": doc.dossier_id,
        "type": doc.type,
        "status": doc.status,
        "filename": doc.original_filename,
        "mime_type": doc.mime_type,
        "file_size_bytes": doc.file_size_bytes,
        "ocr": {
            "provider": doc.ocr_provider,
            "confidence": doc.ocr_confidence,
        },
        "extracted_data": doc.extracted_data,
        "validation_result": doc.validation_result,
        "source_email_subject": doc.source_email_subject,
        "source_email_from": doc.source_email_from,
        "created_at": doc.created_at.isoformat() if doc.created_at else None,
    }


# ─── Helpers internes ───────────────────────────────────────────────────────


async def _sync_profil_pro(db: AsyncSession, professionnel_id: str) -> None:
    """
    Peuple la variable PROFIL_PRO du moteur realtime depuis la BDD locale.
    Le moteur travaille avec des dicts — c'est le pont avec SQLAlchemy.
    """
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
        })


async def _build_dossier_dict(db: AsyncSession, dossier: DossierDB) -> dict:
    """
    Construit un dict compatible avec le moteur realtime depuis le dossier BDD.

    Le moteur de vérification travaille sur des dicts plats — cette fonction
    fait le pont entre SQLAlchemy et le pipeline.
    """
    await _sync_profil_pro(db, dossier.professionnel_id)

    result = await db.execute(
        select(DocumentDB).where(DocumentDB.dossier_id == dossier.id)
    )
    docs = result.scalars().all()

    docs_list = []
    for doc in docs:
        d = {
            "id": doc.id,
            "type": doc.type or "PENDING",
            "filename": doc.original_filename,
            "storage_path": doc.storage_path,
            "status": doc.status,
            "extracted_data": doc.extracted_data or {},
            "ocr_confidence": doc.ocr_confidence,
            "quality": {
                "status": (
                    "ok" if doc.status == "EXTRACTED"
                    else "illisible" if doc.status == "REJECTED"
                    else "en_cours"
                ),
                "confidence": doc.ocr_confidence,
            },
        }
        docs_list.append(d)

    # En version locale, il n'y a plus de distinction vendeur/client.
    # Tous les documents arrivent par l'agent. On garde la structure attendue
    # par le pipeline existant en mettant tout dans documents_vendeur pour
    # rester compatible (le pipeline sera nettoyé en Phase 3.7).
    return {
        "id": dossier.id,
        "type": dossier.type,
        "client_telephone": dossier.client_telephone,
        "client_email": dossier.client_email,
        "client_nom": dossier.client_nom,
        "client_prenom": dossier.client_prenom,
        "vin": dossier.vin,
        "immatriculation": dossier.immatriculation,
        "is_personne_morale": dossier.is_personne_morale,
        "documents_vendeur": docs_list,
        "documents_client": [],
        "documents": docs_list,
        "status": dossier.status,
    }
