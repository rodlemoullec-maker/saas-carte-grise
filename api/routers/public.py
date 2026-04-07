"""
Router public — page client accessible via l'URL permanente du pro.

GET    /public/{slug}               Page publique du pro (infos commerce + formulaire)
POST   /public/{slug}/dossier       Créer un dossier client-initié (docs personnels uniquement)
POST   /public/{slug}/consent       Consentement RGPD (client public)
POST   /public/{slug}/choix-cpi     Choix mode réception CPI (client public)
"""
from __future__ import annotations

import logging
from datetime import datetime
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm.attributes import flag_modified

from api.models.base import get_db
from api.models.dossier import DossierDB
from api.models.professionnel import Professionnel
from notifications.messages import CLIENT as MSG_CLIENT

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/public", tags=["public"])


class PublicDossierRequest(BaseModel):
    """Création dossier par le client public."""
    client_nom: str
    client_prenom: str
    client_telephone: str
    client_email: str | None = None
    intention_type: str | None = None  # "VN", "VO", None (ne sait pas)


# ─── Helpers ────────────────────────────────────────────────────────────────


async def _get_pro_by_slug(db: AsyncSession, slug: str) -> Professionnel:
    """Récupère un pro par son slug public. Lève 404 si inexistant ou inactif."""
    result = await db.execute(
        select(Professionnel).where(Professionnel.slug == slug)
    )
    pro = result.scalar_one_or_none()
    if not pro or not pro.is_active or not pro.page_publique_active:
        raise HTTPException(404, "Page non trouvée")
    return pro


def _generate_reference() -> str:
    import random
    year = datetime.utcnow().year
    seq = random.randint(10000, 99999)
    return f"CG-{year}-{seq}"


# ─── Endpoints ──────────────────────────────────────────────────────────────


@router.get("/{slug}")
async def get_public_page(slug: str, db: AsyncSession = Depends(get_db)):
    """Page publique du pro — informations commerce + formulaire client."""
    pro = await _get_pro_by_slug(db, slug)

    nom = pro.nom_commerce or "votre vendeur"
    type_compte = pro.type_compte or "VENDEUR_HABILITE"
    is_agent = type_compte == "AGENT_HABILITE"

    # Messages adaptés selon le type de pro
    if is_agent:
        finalite = f"Dépôt de vos documents en vue d'une demande de carte grise traitée par {nom}."
        consentement = (
            f"J'accepte que mes documents d'identité soient traités par AutoDoc Pro "
            f"et transmis à {nom} dans le seul but de réaliser ma demande de carte grise. "
            "Mes documents sont lus par Google Document AI et analysés par Claude (Anthropic) "
            "pour en extraire les informations. Ces sous-traitants sont basés aux États-Unis "
            "et ne conservent pas mes données. "
            "J'ai pris connaissance de la politique de confidentialité."
        )
        intro = f"Déposez vos documents pour votre demande de carte grise auprès de {nom}."
    else:
        finalite = f"Pré-dépôt de vos documents d'identité en vue d'une demande de carte grise auprès de {nom}."
        consentement = (
            f"J'accepte que mes documents d'identité soient traités par AutoDoc Pro "
            f"et transmis à {nom} dans le seul but de réaliser ma demande de carte grise. "
            "Mes documents sont lus par Google Document AI et analysés par Claude (Anthropic) "
            "pour en extraire les informations. Ces sous-traitants sont basés aux États-Unis "
            "et ne conservent pas mes données. "
            "J'ai pris connaissance de la politique de confidentialité."
        )
        intro = f"Préparez votre dossier carte grise en déposant vos documents d'identité avant l'achat."

    return {
        "slug": pro.slug,
        "type_compte": type_compte,
        "commerce": {
            "nom": pro.nom_commerce,
            "adresse": pro.adresse,
            "ville": pro.ville,
            "telephone": pro.telephone_commerce,
        },
        "intro": intro,
        "rgpd": {
            "responsable": "AutoDoc Pro",
            "finalite": finalite,
            "base_legale": "Consentement (article 6.1.a RGPD)",
            "conservation": (
                "Vos documents sont traités en temps réel et ne sont pas conservés par nos sous-traitants. "
                "AutoDoc Pro conserve vos documents uniquement le temps de la démarche puis les supprime automatiquement."
            ),
            "droits": "Accès, rectification, suppression, portabilité, opposition — contact : rgpd@cartegrisepro.fr",
        },
        "consentement_texte": consentement,
        "choix_cpi_options": [
            {"id": "main_propre", "label": f"Je récupérerai mon CPI en main propre auprès de {nom}"},
            {"id": "email", "label": "Je souhaite recevoir mon CPI par email", "champ_email_requis": True},
        ],
        "intention_type_options": [
            {"id": "VN", "label": "Véhicule neuf"},
            {"id": "VO", "label": "Véhicule d'occasion"},
            {"id": None, "label": "Je ne sais pas encore"},
        ],
    }


@router.post("/{slug}/dossier", status_code=201)
async def create_public_dossier(
    slug: str,
    request: PublicDossierRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Crée un dossier client-initié.
    Le client dépose ses documents personnels (CNI, permis, domicile).
    Le pro sera notifié dans son espace et prendra le relais après la vente.
    """
    pro = await _get_pro_by_slug(db, slug)
    nom_commerce = pro.nom_commerce or "votre vendeur"

    dossier = DossierDB(
        id=uuid4(),
        reference=_generate_reference(),
        type=None,
        status="PENDING",
        created_by_source="CLIENT",
        professionnel_id=pro.id,
        client_nom=request.client_nom,
        client_prenom=request.client_prenom,
        client_telephone=request.client_telephone,
        client_email=request.client_email,
        metadata_={
            "intention_type": request.intention_type,
            "is_public_client": True,
        },
    )
    db.add(dossier)
    await db.flush()

    # Checklist adaptée selon le type de pro
    type_compte = pro.type_compte or "VENDEUR_HABILITE"
    is_agent = type_compte == "AGENT_HABILITE"

    # Docs identité — toujours requis
    docs_identite = [
        {"type": "CNI", "label": "Pièce d'identité (CNI ou passeport)", "obligatoire": True, "recto_verso": True},
        {"type": "PERMIS", "label": "Permis de conduire", "obligatoire": True, "recto_verso": True},
        {"type": "DOMICILE", "label": "Justificatif de domicile", "obligatoire": True, "recto_verso": False},
    ]

    if is_agent:
        # Agent habilité : la vente a déjà eu lieu entre particuliers
        # Le client doit aussi fournir les docs véhicule
        docs_vehicule = []
        if request.intention_type == "VO":
            docs_vehicule = [
                {"type": "CG_BARREE", "label": "Carte grise barrée", "obligatoire": True, "recto_verso": False},
                {"type": "CERTIFICAT_CESSION", "label": "Certificat de cession signé (Cerfa 15776)", "obligatoire": True, "recto_verso": False},
            ]
        elif request.intention_type == "VN":
            docs_vehicule = [
                {"type": "COC", "label": "Certificat de conformité (COC)", "obligatoire": True, "recto_verso": False},
                {"type": "FACTURE", "label": "Facture d'achat du véhicule", "obligatoire": True, "recto_verso": False},
            ]
        else:
            # Type inconnu — on demandera les docs véhicule plus tard
            docs_vehicule = []

        docs_attendus = docs_vehicule + docs_identite
        message = (
            "Votre dossier est créé. Déposez vos documents : "
            "pièces du véhicule (carte grise barrée, cession) et pièces d'identité "
            "(CNI, permis, justificatif de domicile)."
        ) if docs_vehicule else (
            "Votre dossier est créé. Déposez vos documents d'identité "
            "(CNI ou passeport, permis de conduire, justificatif de domicile). "
            "Les documents véhicule vous seront demandés selon le type de véhicule."
        )
    else:
        # Vendeur (habilité ou non) : la vente n'a pas encore eu lieu
        # Le client ne dépose que ses docs identité
        docs_attendus = docs_identite
        message = (
            "Votre dossier est créé. Vous pouvez maintenant déposer vos documents d'identité "
            "(CNI ou passeport, permis de conduire, justificatif de domicile)."
        )

    # Message de suite adapté
    if is_agent:
        info_suite = f"{nom_commerce} vérifiera votre dossier et soumettra la demande au SIV."
    elif request.intention_type == "VO":
        info_suite = (
            "Pour un véhicule d'occasion, vous serez contacté par SMS après l'achat "
            "pour signer le certificat de cession. C'est une étape obligatoire."
        )
    elif request.intention_type == "VN":
        info_suite = (
            "Sauf besoin de documents complémentaires selon le véhicule, "
            "vos documents devraient suffire."
        )
    else:
        info_suite = (
            "Après l'achat de votre véhicule, si des documents complémentaires "
            "sont nécessaires selon le type de véhicule, vous recevrez un SMS. "
            f"Sinon, {nom_commerce} s'occupe du reste."
        )

    return {
        "dossier_id": str(dossier.id),
        "reference": dossier.reference,
        "status": "PENDING",
        "type_compte": type_compte,
        "info_suite": info_suite,
        "message": message,
        "docs_attendus": docs_attendus,
    }


@router.post("/{slug}/dossier/{dossier_id}/consent")
async def public_consent(
    slug: str,
    dossier_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Consentement RGPD du client public."""
    pro = await _get_pro_by_slug(db, slug)
    dossier = await db.get(DossierDB, dossier_id)
    if not dossier or str(dossier.professionnel_id) != str(pro.id):
        raise HTTPException(404, "Dossier non trouvé")
    if dossier.created_by_source != "CLIENT":
        raise HTTPException(403, "Dossier non public")

    metadata = dossier.metadata_ or {}
    metadata["client_rgpd_consent"] = True
    metadata["client_rgpd_consent_at"] = datetime.utcnow().isoformat()
    dossier.metadata_ = metadata
    flag_modified(dossier, "metadata_")
    await db.flush()
    return {"status": "ok", "message": MSG_CLIENT.get("consentement_ok", "Consentement enregistré.")}


class PublicChoixCPIRequest(BaseModel):
    mode: str
    email: str | None = None


@router.post("/{slug}/dossier/{dossier_id}/choix-cpi")
async def public_choix_cpi(
    slug: str,
    dossier_id: str,
    req: PublicChoixCPIRequest,
    db: AsyncSession = Depends(get_db),
):
    """Choix du mode de réception CPI par le client public."""
    pro = await _get_pro_by_slug(db, slug)
    dossier = await db.get(DossierDB, dossier_id)
    if not dossier or str(dossier.professionnel_id) != str(pro.id):
        raise HTTPException(404, "Dossier non trouvé")
    if dossier.created_by_source != "CLIENT":
        raise HTTPException(403, "Dossier non public")

    if req.mode not in ("email", "main_propre"):
        raise HTTPException(422, "Mode invalide.")
    if req.mode == "email" and (not req.email or "@" not in req.email):
        raise HTTPException(422, "Adresse email requise.")

    metadata = dossier.metadata_ or {}
    metadata["cpi_mode"] = req.mode
    if req.email:
        metadata["cpi_email"] = req.email
    dossier.metadata_ = metadata
    flag_modified(dossier, "metadata_")
    await db.flush()

    nom_commerce = pro.nom_commerce or "votre vendeur"
    if req.mode == "email":
        msg = f"Votre CPI sera envoyé à {req.email} une fois le dossier finalisé."
    else:
        msg = f"Vous récupérerez votre CPI en main propre auprès de {nom_commerce}."
    return {"status": "ok", "message": msg}
