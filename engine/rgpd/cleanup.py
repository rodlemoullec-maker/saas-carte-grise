"""
Nettoyage RGPD — suppression des donnees client apres finalisation du dossier.

Quand un dossier passe en CERFA_GENERE :
1. Les fichiers documents client sont supprimes du stockage (S3/local)
2. Le texte OCR brut est supprime de la BDD
3. Les donnees extraites detaillees sont supprimees
4. Seul un resume anonymise est conserve pour l'archivage pro (5 ans)

Ce qui est CONSERVE (archivage pro 5 ans) :
- Reference dossier, type VN/VO, dates
- VIN, immatriculation
- Nom du titulaire (necessaire pour l'archivage)
- Diagnostic, estimation taxes
- Montant facture

Ce qui est SUPPRIME :
- Fichiers documents client (CNI, permis, domicile) du stockage
- Texte OCR brut des documents client
- Donnees extraites detaillees (date naissance, lieu naissance, MRZ, etc.)
- Metadata client (consentement, choix CPI, email CPI)
- Prenom, telephone et email du client (non necessaires a l'archivage)
"""
from __future__ import annotations

import logging
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


async def cleanup_client_data_after_cerfa(
    db: AsyncSession,
    dossier_id: UUID,
) -> dict:
    """
    Supprime les donnees personnelles client apres generation du Cerfa.
    Appele automatiquement quand le dossier passe en CERFA_GENERE.

    Retourne un resume de ce qui a ete supprime.
    """
    from api.models.document import DocumentDB
    from api.models.dossier import DossierDB
    from storage.document_store import get_document_store

    store = get_document_store()
    supprime = {"fichiers": 0, "documents_db": 0}

    # 1. Trouver les documents client
    result = await db.execute(
        select(DocumentDB).where(
            DocumentDB.dossier_id == dossier_id,
            DocumentDB.source == "client",
        )
    )
    client_docs = result.scalars().all()

    for doc in client_docs:
        # Supprimer le fichier du stockage
        try:
            await store.delete(doc.storage_path)
            supprime["fichiers"] += 1
        except Exception as e:
            logger.warning(f"[RGPD] Impossible de supprimer {doc.storage_path}: {e}")

        # Supprimer les donnees sensibles de la BDD
        # On garde le type et le statut pour l'archivage, mais on efface le contenu
        doc.ocr_raw_text = None
        doc.extracted_data = {"supprime_rgpd": True, "type_original": doc.type}
        doc.storage_path = "supprime_rgpd"
        doc.sha256 = "supprime_rgpd"
        supprime["documents_db"] += 1

    # 2. Anonymiser les données personnelles du client sur le dossier
    # On conserve client_nom (nécessaire pour l'archivage pro 5 ans)
    # On supprime téléphone, email, prénom (non nécessaires à l'archivage)
    dossier = await db.get(DossierDB, dossier_id)
    if dossier:
        dossier.client_telephone = None
        dossier.client_email = None
        dossier.client_prenom = None

    # 3. Nettoyer les metadata client du dossier
    if dossier and dossier.metadata_:
        metadata = dict(dossier.metadata_)
        # Garder uniquement les infos non sensibles
        keys_to_keep = {"cpi_mode", "choix_assurance_pro", "assurance_flotte_couvre"}
        keys_to_remove = [k for k in metadata if k not in keys_to_keep]
        for k in keys_to_remove:
            metadata.pop(k, None)
        metadata["rgpd_cleanup_done"] = True
        dossier.metadata_ = metadata

        from sqlalchemy.orm.attributes import flag_modified
        flag_modified(dossier, 'metadata_')

    await db.flush()

    logger.info(
        f"[RGPD] Dossier {dossier_id} nettoye : "
        f"{supprime['fichiers']} fichiers supprimes, "
        f"{supprime['documents_db']} docs client anonymises"
    )

    return supprime


async def cleanup_expired_dossiers(db: AsyncSession, retention_days: int = 1825) -> int:
    """
    Supprime les dossiers archives depuis plus de 5 ans (1825 jours).
    A executer periodiquement (cron).

    Retourne le nombre de dossiers supprimes.
    """
    from datetime import datetime, timedelta
    from api.models.dossier import DossierDB
    from api.models.document import DocumentDB

    cutoff = datetime.utcnow() - timedelta(days=retention_days)
    count = 0

    result = await db.execute(
        select(DossierDB).where(
            DossierDB.status.in_(["CERFA_GENERE", "SOUMIS", "CLOSED"]),
            DossierDB.created_at < cutoff,
        )
    )
    old_dossiers = result.scalars().all()

    for dossier in old_dossiers:
        # Supprimer tous les documents
        docs = await db.execute(
            select(DocumentDB).where(DocumentDB.dossier_id == dossier.id)
        )
        for doc in docs.scalars().all():
            await db.delete(doc)

        # Supprimer le dossier
        await db.delete(dossier)
        count += 1

    if count > 0:
        await db.flush()
        logger.info(f"[RGPD] {count} dossiers expires supprimes (> {retention_days} jours)")

    return count
