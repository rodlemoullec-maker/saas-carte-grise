"""
Worker pipeline — orchestration du traitement d'un dossier.

Tâches Celery :
  process_dossier(dossier_id)   → pipeline complet (Phase 0 + Phase 1)
  run_ocr(document_id)          → OCR + extraction d'un document
  run_phase2(dossier_id)        → KYC + soumission SIV / livraison dossier

Architecture :
  - Redis comme broker Celery
  - Chaque tâche est idempotente (retry safe)
  - Max 3 retries avec backoff exponentiel
  - Le statut dossier/document est mis à jour à chaque étape
"""
from __future__ import annotations

import logging
from uuid import UUID

from celery import Celery

from config.settings import get_settings

logger = logging.getLogger(__name__)

settings = get_settings()

app = Celery(
    "carte_grise_pipeline",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
)

app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="Europe/Paris",
    enable_utc=True,
    task_track_started=True,
    task_acks_late=True,        # ACK après exécution (pas avant)
    worker_prefetch_multiplier=1,  # 1 tâche à la fois par worker
    task_default_retry_delay=60,   # 60s entre retries
    task_max_retries=3,
)


@app.task(bind=True, max_retries=3, default_retry_delay=60)
def process_dossier(self, dossier_id: str) -> dict:
    """
    Pipeline complet pour un dossier :

    1. Charger le dossier + documents depuis la BDD
    2. Phase 0 (VO) : HistoVec check
    3. Pour chaque document : OCR + extraction + validation
    4. Phase 1 : cross-checks + scoring + décision + estimation taxes
    5. MAJ statut dossier + notification pro
    """
    from api.models.base import get_session_factory
    from engine.pipeline.phase1 import Phase1Pipeline
    import asyncio

    logger.info(f"[Pipeline] Démarrage dossier {dossier_id}")

    try:
        # Le pipeline est synchrone — on wrappe les appels DB async
        loop = asyncio.new_event_loop()
        result = loop.run_until_complete(_process_dossier_async(dossier_id))
        loop.close()
        return result
    except Exception as exc:
        logger.error(f"[Pipeline] Erreur dossier {dossier_id}: {exc}")
        raise self.retry(exc=exc)


@app.task(bind=True, max_retries=3, default_retry_delay=30)
def run_ocr(self, document_id: str) -> dict:
    """
    Lance l'OCR + classification + extraction sur un document.

    1. Récupérer le fichier depuis le store
    2. Envoyer au provider OCR
    3. Classifier le type de document (si pas déjà défini)
    4. Extraire les données structurées
    5. MAJ Document en BDD
    """
    import asyncio

    logger.info(f"[OCR] Démarrage document {document_id}")

    try:
        loop = asyncio.new_event_loop()
        result = loop.run_until_complete(_run_ocr_async(document_id))
        loop.close()
        return result
    except Exception as exc:
        logger.error(f"[OCR] Erreur document {document_id}: {exc}")
        raise self.retry(exc=exc)


@app.task(bind=True, max_retries=3, default_retry_delay=120)
def run_phase2(self, dossier_id: str) -> dict:
    """
    Phase 2 — KYC + soumission.

    Full Service : KYC → (conditionnel NIV.3) → extension SIV → CPI
    SaaS : KYC → livraison dossier prêt
    """
    logger.info(f"[Phase2] Démarrage dossier {dossier_id}")
    # TODO: implémenter après obtention habilitation SIV
    return {"status": "not_implemented", "dossier_id": dossier_id}


# ──── Implémentation async ────────────────────────────────────────────────

async def _process_dossier_async(dossier_id: str) -> dict:
    """Implémentation async du pipeline complet."""
    from api.models.base import get_session_factory
    from api.models.dossier import DossierDB
    from api.models.document import DocumentDB
    from engine.ocr.classifier import DocumentClassifier
    from engine.ocr.extractor import DocumentExtractor
    from engine.pipeline.phase1 import Phase1Pipeline, ExtractedDocuments
    from engine.validators.completeness import FlowType
    from integrations.ocr_providers.base import OCRResult, OCRPage
    from storage.document_store import get_document_store
    from sqlalchemy import select

    factory = get_session_factory()
    async with factory() as db:
        # 1. Charger le dossier
        dossier = await db.get(DossierDB, UUID(dossier_id))
        if not dossier:
            return {"error": "Dossier non trouvé"}

        dossier.status = "PROCESSING"
        await db.flush()

        # 2. Charger les documents
        result = await db.execute(
            select(DocumentDB).where(DocumentDB.dossier_id == UUID(dossier_id))
        )
        documents = result.scalars().all()

        # 3. OCR + extraction pour chaque document non encore traité
        store = get_document_store()
        classifier = DocumentClassifier()
        extractor = DocumentExtractor()

        for doc in documents:
            if doc.status in ("EXTRACTED", "VALIDATED"):
                continue  # Déjà traité

            try:
                file_bytes = await store.get(doc.storage_path)

                # OCR (simplifié — en prod, appel au provider réel)
                # TODO: appeler le vrai OCR provider
                ocr_result = OCRResult(
                    pages=[OCRPage(page_number=1, text="", confidence=0.0)],
                    full_text="",
                    average_confidence=0.0,
                    provider="pending",
                )

                # Classifier si type pas encore défini
                if doc.type == "PENDING" or not doc.type:
                    classification = classifier.classify(ocr_result.full_text)
                    doc.type = classification.doc_type.value
                    doc.auto_classified = True
                    doc.classification_confidence = classification.confidence

                # Extraire
                from engine.models.documents import DocumentType
                try:
                    doc_type = DocumentType(doc.type)
                    extracted = extractor.extract(doc_type, ocr_result)
                    doc.extracted_data = extracted
                except (ValueError, KeyError):
                    pass

                doc.ocr_confidence = ocr_result.average_confidence
                doc.status = "EXTRACTED"

            except Exception as e:
                logger.error(f"[OCR] Erreur doc {doc.id}: {e}")
                doc.status = "REJECTED"

        await db.flush()

        # 4. Pipeline Phase 1
        # TODO: construire ExtractedDocuments depuis les extracted_data des docs
        # Pour l'instant, on marque le dossier comme nécessitant les données OCR réelles
        flow_type = FlowType.VO if "OCCASION" in dossier.type else FlowType.VN

        # Mise à jour dossier avec résultat placeholder
        dossier.status = "CORRECTION"  # En attente d'OCR réel
        dossier.diagnostic = "ORANGE"
        await db.commit()

        return {
            "status": "processed",
            "dossier_id": dossier_id,
            "documents_processed": len(documents),
        }


async def _run_ocr_async(document_id: str) -> dict:
    """OCR async pour un document individuel."""
    from api.models.base import get_session_factory
    from api.models.document import DocumentDB
    from engine.ocr.classifier import DocumentClassifier
    from engine.ocr.extractor import DocumentExtractor
    from storage.document_store import get_document_store

    factory = get_session_factory()
    async with factory() as db:
        doc = await db.get(DocumentDB, UUID(document_id))
        if not doc:
            return {"error": "Document non trouvé"}

        doc.status = "PROCESSING"
        await db.flush()

        store = get_document_store()
        file_bytes = await store.get(doc.storage_path)

        # TODO: appeler le vrai provider OCR (Google DocAI / Azure)
        # ocr_result = await ocr_provider.process_document(file_bytes, doc.mime_type)

        doc.status = "EXTRACTED"
        await db.commit()

        return {"status": "extracted", "document_id": document_id}
