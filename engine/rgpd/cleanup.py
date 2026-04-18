"""
Nettoyage RGPD — version locale d'Imatra.

Quand un dossier passe en CERFA_GENERE :
1. Tous les fichiers documents sont supprimés du stockage local chiffré
2. Le texte OCR brut est supprimé de la BDD SQLite
3. Les données extraites détaillées sont anonymisées
4. Seul un résumé minimal est conservé pour l'archivage légal (5 ans)

Ce qui est CONSERVÉ (archivage légal 5 ans) :
- Référence dossier, type VN/VO, dates
- VIN, immatriculation
- Nom du titulaire (obligation Code de la route)
- Diagnostic, estimation taxes

Ce qui est SUPPRIMÉ :
- Fichiers documents (CNI, permis, domicile, COC, facture, etc.)
- Texte OCR brut
- Données extraites détaillées (date naissance, lieu naissance, MRZ, etc.)
- Prénom, téléphone et email du client
"""
from __future__ import annotations

import logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


async def cleanup_client_data_after_cerfa(
    db: AsyncSession,
    dossier_id: str,
) -> dict:
    """
    Supprime les données personnelles client après génération du Cerfa.
    Appelé automatiquement quand le dossier passe en CERFA_GENERE.

    Retourne un résumé de ce qui a été supprimé.
    """
    from api.models.document import DocumentDB
    from api.models.dossier import DossierDB
    from storage.document_store import get_document_store

    store = get_document_store()
    supprime = {"fichiers": 0, "documents_db": 0}

    # 1. Récupérer tous les documents du dossier
    result = await db.execute(
        select(DocumentDB).where(DocumentDB.dossier_id == dossier_id)
    )
    docs = result.scalars().all()

    for doc in docs:
        # Supprimer le fichier chiffré du stockage local
        try:
            await store.delete(doc.storage_path)
            supprime["fichiers"] += 1
        except Exception as e:
            logger.warning(f"[RGPD] Impossible de supprimer {doc.storage_path}: {e}")

        # Anonymiser les données sensibles en BDD
        # On garde le type et le statut pour l'archivage, mais on efface le contenu
        doc.ocr_raw_text = None
        doc.extracted_data = {"supprime_rgpd": True, "type_original": doc.type}
        doc.storage_path = "supprime_rgpd"
        doc.sha256 = "supprime_rgpd"
        doc.source_email_subject = None
        doc.source_email_from = None
        supprime["documents_db"] += 1

    # 2. Anonymiser les données personnelles du client sur le dossier
    # Conservé pour archivage légal : client_nom + reference + vin + immatriculation
    # Supprimé : prénom, téléphone, email, métadonnées sensibles
    dossier = await db.get(DossierDB, dossier_id)
    if dossier:
        dossier.client_telephone = None
        dossier.client_email = None
        dossier.client_prenom = None

        if dossier.metadata_:
            metadata = dict(dossier.metadata_)
            metadata = {"rgpd_cleanup_done": True}
            dossier.metadata_ = metadata
            from sqlalchemy.orm.attributes import flag_modified
            flag_modified(dossier, 'metadata_')

    await db.flush()

    logger.info(
        f"[RGPD] Dossier {dossier_id} nettoyé : "
        f"{supprime['fichiers']} fichiers supprimés, "
        f"{supprime['documents_db']} documents anonymisés"
    )

    return supprime


async def cleanup_expired_dossiers(db: AsyncSession, retention_days: int = 1825) -> int:
    """
    Supprime les dossiers archivés depuis plus de 5 ans (1825 jours).
    À exécuter périodiquement par l'agent (manuellement ou via une tâche planifiée).

    Retourne le nombre de dossiers supprimés.
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
        docs = await db.execute(
            select(DocumentDB).where(DocumentDB.dossier_id == dossier.id)
        )
        for doc in docs.scalars().all():
            await db.delete(doc)

        await db.delete(dossier)
        count += 1

    if count > 0:
        await db.flush()
        logger.info(f"[RGPD] {count} dossiers expirés supprimés (> {retention_days} jours)")

    return count
