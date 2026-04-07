"""
Limite de volume + facturation — plafond mensuel, batch de paiement, essai gratuit.

Seuils volume :
- NORMAL : jusqu'à 50 dossiers/mois
- ALERTE : 50-100 dossiers/mois (gros volume, à surveiller)
- BLOCAGE : 100+ dossiers/mois (volume de mandataire en ligne → investigation)

Facturation :
- 5 premiers dossiers = essai gratuit (pas de paiement requis)
- Ensuite, batch de 5 max : le pro doit payer les dossiers traités avant d'en créer de nouveaux
"""
from __future__ import annotations

import logging
from datetime import datetime
from uuid import UUID

from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession

from api.models.dossier import DossierDB

logger = logging.getLogger(__name__)

# Seuils mensuels
SEUIL_ALERTE = 50
SEUIL_BLOCAGE = 100

# Facturation
BATCH_MAX = 5
ESSAI_GRATUIT = 5


async def verifier_volume_mensuel(db: AsyncSession, professionnel_id: UUID) -> dict:
    """
    Vérifie le nombre de dossiers créés ce mois par un pro.
    """
    debut_mois = datetime.utcnow().replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    result = await db.execute(
        select(func.count(DossierDB.id)).where(
            DossierDB.professionnel_id == professionnel_id,
            DossierDB.created_at >= debut_mois,
        )
    )
    count = result.scalar() or 0

    if count >= SEUIL_BLOCAGE:
        logger.warning(f"[VOLUME] Pro {professionnel_id} : {count} dossiers ce mois — BLOCAGE")
        return {
            "status": "bloque",
            "count": count,
            "message": (
                f"Vous avez créé {count} dossiers ce mois. "
                f"Ce volume dépasse la limite autorisée ({SEUIL_BLOCAGE}/mois). "
                "Contactez-nous pour débloquer votre compte."
            ),
        }

    if count >= SEUIL_ALERTE:
        logger.info(f"[VOLUME] Pro {professionnel_id} : {count} dossiers ce mois — ALERTE")
        return {
            "status": "alerte",
            "count": count,
            "message": f"Volume élevé : {count} dossiers ce mois.",
        }

    return {"status": "ok", "count": count, "message": None}


async def verifier_facturation(db: AsyncSession, professionnel_id: UUID) -> dict:
    """
    Vérifie si le pro peut créer un nouveau dossier selon son état de facturation.

    Règles :
    - Les 5 premiers dossiers (tous statuts confondus) = essai gratuit
    - Au-delà, le pro ne peut pas avoir plus de 5 dossiers traités (CERFA_GENERE)
      non payés. S'il en a 5 ou plus non payés, il doit payer avant de continuer.

    Retourne :
    - status: "ok" | "essai" | "bloque"
    - total_dossiers: nombre total de dossiers du pro
    - non_payes: nombre de dossiers traités non payés
    - message: explication
    """
    # Compter le total de dossiers du pro (tous statuts)
    result_total = await db.execute(
        select(func.count(DossierDB.id)).where(
            DossierDB.professionnel_id == professionnel_id,
        )
    )
    total = result_total.scalar() or 0

    # Période d'essai : les 5 premiers dossiers
    if total < ESSAI_GRATUIT:
        return {
            "status": "essai",
            "total_dossiers": total,
            "non_payes": 0,
            "restant_essai": ESSAI_GRATUIT - total,
            "message": f"Essai gratuit : {ESSAI_GRATUIT - total} dossier(s) restant(s) sans avance de frais.",
        }

    # Au-delà de l'essai : compter les dossiers traités non payés
    result_non_payes = await db.execute(
        select(func.count(DossierDB.id)).where(
            DossierDB.professionnel_id == professionnel_id,
            DossierDB.status == "CERFA_GENERE",
            DossierDB.payment_captured == False,
        )
    )
    non_payes = result_non_payes.scalar() or 0

    if non_payes >= BATCH_MAX:
        logger.info(f"[FACTURATION] Pro {professionnel_id} : {non_payes} dossiers non payés — BLOCAGE")
        return {
            "status": "bloque",
            "total_dossiers": total,
            "non_payes": non_payes,
            "message": (
                f"Vous avez {non_payes} dossier(s) traité(s) en attente de règlement. "
                f"Réglez vos dossiers en cours pour pouvoir en créer de nouveaux."
            ),
        }

    return {
        "status": "ok",
        "total_dossiers": total,
        "non_payes": non_payes,
        "message": None,
    }


async def rapport_surveillance(db: AsyncSession) -> list[dict]:
    """Rapport de surveillance — liste les pros avec un volume anormal ce mois."""
    debut_mois = datetime.utcnow().replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    result = await db.execute(
        select(
            DossierDB.professionnel_id,
            func.count(DossierDB.id).label("count"),
        )
        .where(DossierDB.created_at >= debut_mois)
        .group_by(DossierDB.professionnel_id)
        .having(func.count(DossierDB.id) >= SEUIL_ALERTE)
        .order_by(func.count(DossierDB.id).desc())
    )

    return [
        {"professionnel_id": str(row[0]), "dossiers_ce_mois": row[1], "niveau": "bloque" if row[1] >= SEUIL_BLOCAGE else "alerte"}
        for row in result.all()
    ]
