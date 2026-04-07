"""
Router professionnel — paramétrage profil, cachet, signature, Kbis.

POST   /professionnel/profil           Créer/mettre à jour le profil
GET    /professionnel/profil           Consulter le profil
POST   /professionnel/profil/cachet    Uploader le cachet commercial
POST   /professionnel/profil/signature Uploader la signature
POST   /professionnel/profil/kbis      Uploader le Kbis (OCR + extraction SIREN)
"""
from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from api.models.base import get_db
from api.models.professionnel import Professionnel
from api.auth import get_current_pro_transition as get_current_pro
from storage.document_store import get_document_store
from notifications.messages import PRO as MSG_PRO

router = APIRouter(prefix="/professionnel", tags=["professionnel"])


class ProfilSetupRequest(BaseModel):
    nom_commerce: str
    adresse: str
    telephone_commerce: str
    email_commerce: str | None = None
    type_compte: str = "VENDEUR_HABILITE"  # VENDEUR_HABILITE | VENDEUR_NON_HABILITE | AGENT_HABILITE
    assurance_flotte_vn: bool = False
    assurance_flotte_vo: bool = False
    demander_assurance_client_vn: bool = False
    demander_assurance_client_vo: bool = False
    # Infos agent (VENDEUR_NON_HABILITE uniquement)
    agent_nom: str | None = None
    agent_siret: str | None = None
    agent_numero_habilitation: str | None = None
    agent_telephone: str | None = None
    agent_email: str | None = None


@router.post("/profil")
async def setup_profil(
    req: ProfilSetupRequest,
    pro: Professionnel = Depends(get_current_pro),
    db: AsyncSession = Depends(get_db),
):
    """
    Paramétrage initial du profil pro.

    Le pro renseigne : nom commerce, adresse, téléphone, assurance flotte.
    Cachet, signature et Kbis sont uploadés séparément.
    Ces infos sont intégrées dans le SMS envoyé au client.
    """
    pro.nom_commerce = req.nom_commerce
    pro.adresse = req.adresse
    pro.telephone_commerce = req.telephone_commerce
    pro.email_commerce = req.email_commerce
    pro.assurance_flotte_vn = req.assurance_flotte_vn
    pro.assurance_flotte_vo = req.assurance_flotte_vo
    pro.demander_assurance_client_vn = req.demander_assurance_client_vn if not req.assurance_flotte_vn else False
    pro.demander_assurance_client_vo = req.demander_assurance_client_vo if not req.assurance_flotte_vo else False

    # Type de compte
    if req.type_compte in ("VENDEUR_HABILITE", "VENDEUR_NON_HABILITE", "AGENT_HABILITE"):
        pro.type_compte = req.type_compte

    # Infos agent (vendeur non habilité uniquement)
    if pro.type_compte == "VENDEUR_NON_HABILITE":
        pro.agent_nom = req.agent_nom
        pro.agent_siret = req.agent_siret
        pro.agent_numero_habilitation = req.agent_numero_habilitation
        pro.agent_telephone = req.agent_telephone
        pro.agent_email = req.agent_email
    else:
        pro.agent_nom = None
        pro.agent_siret = None
        pro.agent_numero_habilitation = None
        pro.agent_telephone = None
        pro.agent_email = None

    _update_setup_complete(pro)
    await db.flush()

    message = "Informations enregistrees."
    if pro.setup_complete:
        message = MSG_PRO["profil_pret"]

    return {"status": "ok", "message": message, "setup_complete": pro.setup_complete}


class TypeCompteRequest(BaseModel):
    type_compte: str


@router.post("/profil/type-compte")
async def update_type_compte(
    req: TypeCompteRequest,
    pro: Professionnel = Depends(get_current_pro),
    db: AsyncSession = Depends(get_db),
):
    """Change le type de compte sans toucher au reste du profil."""
    if req.type_compte not in ("VENDEUR_HABILITE", "VENDEUR_NON_HABILITE", "AGENT_HABILITE"):
        raise HTTPException(422, "Type de compte invalide")

    pro.type_compte = req.type_compte

    # Reset agent info si plus vendeur non habilité
    if pro.type_compte != "VENDEUR_NON_HABILITE":
        pro.agent_nom = None
        pro.agent_siret = None
        pro.agent_numero_habilitation = None
        pro.agent_telephone = None
        pro.agent_email = None

    _update_setup_complete(pro)
    await db.flush()

    return {"status": "ok", "type_compte": pro.type_compte, "setup_complete": pro.setup_complete}


@router.post("/profil/accepter-cgv")
async def accepter_cgv(
    pro: Professionnel = Depends(get_current_pro),
    db: AsyncSession = Depends(get_db),
):
    """Le pro accepte les CGV (incluant clause anti-concurrence et limite de volume)."""
    pro.cgv_acceptees = True
    await db.flush()
    return {"status": "ok", "message": "Conditions générales acceptées."}


@router.get("/admin/surveillance")
async def surveillance_volume(db: AsyncSession = Depends(get_db)):
    """Endpoint admin — liste des comptes avec volume anormal ce mois."""
    from api.guards.volume_limit import rapport_surveillance
    rapport = await rapport_surveillance(db)
    return {"mois_en_cours": rapport}


@router.get("/profil")
async def get_profil(
    pro: Professionnel = Depends(get_current_pro),
    db: AsyncSession = Depends(get_db),
):
    return {
        "id": str(pro.id),
        "nom_commerce": pro.nom_commerce,
        "adresse": pro.adresse,
        "telephone_commerce": pro.telephone_commerce,
        "email_commerce": pro.email_commerce,
        "siret": pro.siret,
        "raison_sociale": pro.raison_sociale,
        "type_compte": pro.type_compte,
        "cachet_uploaded": pro.cachet_path is not None,
        "signature_uploaded": pro.signature_path is not None,
        "kbis_uploaded": pro.kbis_path is not None,
        "assurance_flotte_vn": pro.assurance_flotte_vn,
        "assurance_flotte_vo": pro.assurance_flotte_vo,
        "demander_assurance_client_vn": pro.demander_assurance_client_vn,
        "demander_assurance_client_vo": pro.demander_assurance_client_vo,
        "setup_complete": pro.setup_complete,
        "cgv_acceptees": pro.cgv_acceptees,
        # Infos agent (vendeur non habilité)
        "agent_nom": pro.agent_nom,
        "agent_siret": pro.agent_siret,
        "agent_numero_habilitation": pro.agent_numero_habilitation,
        "agent_telephone": pro.agent_telephone,
        "agent_email": pro.agent_email,
        # Page publique
        "slug": pro.slug,
        "page_publique_active": pro.page_publique_active,
        "page_publique_url": f"https://app.autodocpro.fr/public/{pro.slug}" if pro.slug else None,
    }


@router.post("/profil/cachet")
async def upload_cachet(
    file: UploadFile,
    pro: Professionnel = Depends(get_current_pro),
    db: AsyncSession = Depends(get_db),
):
    store = get_document_store()
    file_bytes = await file.read()
    path = f"profil/{pro.id}/cachet/{file.filename}"
    await store.save(file_bytes, path, file.content_type)

    pro.cachet_path = path
    _update_setup_complete(pro)
    await db.flush()

    return {"status": "ok", "message": "Cachet enregistre."}


@router.post("/profil/signature")
async def upload_signature(
    file: UploadFile,
    pro: Professionnel = Depends(get_current_pro),
    db: AsyncSession = Depends(get_db),
):
    store = get_document_store()
    file_bytes = await file.read()
    path = f"profil/{pro.id}/signature/{file.filename}"
    await store.save(file_bytes, path, file.content_type)

    pro.signature_path = path
    _update_setup_complete(pro)
    await db.flush()

    return {"status": "ok", "message": "Signature enregistree."}


@router.post("/profil/kbis")
async def upload_kbis(
    file: UploadFile,
    pro: Professionnel = Depends(get_current_pro),
    db: AsyncSession = Depends(get_db),
):
    """
    Upload du Kbis — OCR + extraction SIREN/raison sociale.
    Auto-remplit les infos du profil.
    """
    store = get_document_store()
    file_bytes = await file.read()
    path = f"profil/{pro.id}/kbis/{file.filename}"
    await store.save(file_bytes, path, file.content_type)

    pro.kbis_path = path

    # OCR via Google Document AI
    from engine.pipeline.realtime import _ocr_google_docai, classify_document, extract_data

    mime = file.content_type or "application/pdf"
    raw_text = ""
    ocr_confidence = 0.0

    try:
        goo = _ocr_google_docai(file_bytes, mime)
        raw_text = goo["text"]
        ocr_confidence = goo["confidence"]
    except Exception:
        pass

    # Extraire les infos du Kbis
    kbis_extracted = extract_data("KBIS", raw_text)

    # Verifier la date du Kbis (< 3 mois)
    kbis_warning = None
    from datetime import timedelta
    date_kbis = kbis_extracted.get("date_kbis") or kbis_extracted.get("date_document")
    if date_kbis:
        try:
            from datetime import datetime
            date_obj = datetime.strptime(date_kbis, "%d/%m/%Y")
            if (datetime.utcnow() - date_obj) > timedelta(days=90):
                kbis_warning = f"Kbis date du {date_kbis} (plus de 3 mois). Un Kbis recent est recommande."
        except (ValueError, TypeError):
            pass

    # Sauvegarder les infos extraites
    pro.kbis_extracted = kbis_extracted

    # Auto-remplir SIREN, raison sociale, adresse depuis le Kbis
    if kbis_extracted.get("siren"):
        pro.siret = kbis_extracted["siren"]
        pro.siren = kbis_extracted["siren"][:9] if len(kbis_extracted["siren"]) >= 9 else kbis_extracted["siren"]
    if kbis_extracted.get("raison_sociale"):
        pro.raison_sociale = kbis_extracted["raison_sociale"]
        if not pro.nom_commerce:
            pro.nom_commerce = kbis_extracted["raison_sociale"]
    if kbis_extracted.get("adresse"):
        pro.adresse = kbis_extracted["adresse"]

    # Vérification NAF automatique via API SIRENE
    naf_result = None
    siret_for_check = pro.siret or kbis_extracted.get("siren")
    if siret_for_check:
        from api.guards.naf_filter import verifier_siret
        naf_result = await verifier_siret(siret_for_check)
        if naf_result["status"] == "refuse":
            # Ne pas bloquer l'upload mais signaler
            pro.is_active = False
            await db.flush()
            return {
                "status": "refuse",
                "message": naf_result["raison"],
                "naf": naf_result["naf"],
                "nom_sirene": naf_result["nom"],
            }

    _update_setup_complete(pro)
    await db.flush()

    result = {
        "status": "ok",
        "message": "Kbis enregistre — informations extraites automatiquement.",
        "ocr_confidence": ocr_confidence,
        "extracted": kbis_extracted,
    }
    if kbis_warning:
        result["warning"] = kbis_warning
    if naf_result:
        result["naf_verification"] = naf_result

    return result


# ─── Page publique (URL permanente) ─────────────────────────────────────────


class SlugRequest(BaseModel):
    slug: str


@router.post("/profil/page-publique")
async def setup_page_publique(
    req: SlugRequest,
    pro: Professionnel = Depends(get_current_pro),
    db: AsyncSession = Depends(get_db),
):
    """
    Configure le slug de la page publique du pro.
    Le slug doit être unique, en minuscules, sans espaces.
    Active automatiquement la page publique.
    """
    import re
    slug = req.slug.strip().lower()
    slug = re.sub(r"[^a-z0-9-]", "-", slug)
    slug = re.sub(r"-+", "-", slug).strip("-")

    if len(slug) < 3:
        raise HTTPException(422, "Le slug doit faire au moins 3 caractères.")
    if len(slug) > 80:
        raise HTTPException(422, "Le slug est trop long (80 caractères max).")

    # Vérifier unicité
    from sqlalchemy import select
    existing = await db.execute(
        select(Professionnel).where(Professionnel.slug == slug, Professionnel.id != pro.id)
    )
    if existing.scalar_one_or_none():
        raise HTTPException(409, f"Le slug '{slug}' est déjà utilisé par un autre compte.")

    pro.slug = slug
    pro.page_publique_active = True
    await db.flush()

    return {
        "status": "ok",
        "slug": slug,
        "page_publique_active": True,
        "url": f"https://app.autodocpro.fr/public/{slug}",
        "message": f"Votre page publique est accessible à l'adresse : /public/{slug}",
    }


@router.delete("/profil/page-publique")
async def disable_page_publique(
    pro: Professionnel = Depends(get_current_pro),
    db: AsyncSession = Depends(get_db),
):
    """Désactive la page publique (conserve le slug pour réactivation future)."""
    pro.page_publique_active = False
    await db.flush()
    return {"status": "ok", "page_publique_active": False, "message": "Page publique désactivée."}


@router.get("/profil/page-publique")
async def get_page_publique(
    pro: Professionnel = Depends(get_current_pro),
):
    """Retourne l'état de la page publique du pro."""
    return {
        "slug": pro.slug,
        "page_publique_active": pro.page_publique_active,
        "url": f"https://app.autodocpro.fr/public/{pro.slug}" if pro.slug else None,
    }


# ─── Helpers ────────────────────────────────────────────────────────────────


def _update_setup_complete(pro: Professionnel) -> None:
    """Met à jour le flag setup_complete selon le type de compte."""
    base_ok = bool(
        pro.nom_commerce
        and pro.adresse
        and pro.telephone_commerce
        and pro.cachet_path
        and pro.signature_path
        and pro.kbis_path
    )
    if pro.type_compte == "VENDEUR_NON_HABILITE":
        # Le vendeur non habilité doit aussi avoir renseigné son agent
        pro.setup_complete = base_ok and bool(
            pro.agent_nom
            and pro.agent_siret
            and pro.agent_numero_habilitation
        )
    else:
        pro.setup_complete = base_ok
