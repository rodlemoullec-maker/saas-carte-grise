"""
Modèle Document — un fichier uploadé dans un dossier.
"""
from __future__ import annotations

import uuid

from sqlalchemy import Float, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from api.models.base import Base, TimestampMixin


class DocumentDB(Base, TimestampMixin):
    __tablename__ = "documents"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    dossier_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("dossiers.id"), index=True,
    )

    # Type et statut
    type: Mapped[str] = mapped_column(String(40))  # DocumentType enum value
    status: Mapped[str] = mapped_column(String(20), default="PENDING")  # PENDING → PROCESSING → EXTRACTED → VALIDATED / REJECTED

    # Fichier
    storage_path: Mapped[str] = mapped_column(String(500))  # Chemin logique dans le store
    original_filename: Mapped[str] = mapped_column(String(255))
    mime_type: Mapped[str] = mapped_column(String(100))
    file_size_bytes: Mapped[int] = mapped_column(Integer)
    sha256: Mapped[str] = mapped_column(String(64))  # Intégrité + dédoublonnage

    # OCR
    ocr_provider: Mapped[str | None] = mapped_column(String(50), nullable=True)
    ocr_confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    ocr_raw_text: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Extraction structurée (résultat OCR → modèle Pydantic sérialisé)
    extracted_data: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    # Validation individuelle
    validation_result: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    # Qualité
    page_coverage: Mapped[float | None] = mapped_column(Float, nullable=True)
    detected_language: Mapped[str | None] = mapped_column(String(10), nullable=True)

    # Classifié automatiquement ?
    auto_classified: Mapped[bool] = mapped_column(default=False)
    classification_confidence: Mapped[float | None] = mapped_column(Float, nullable=True)

    # Relation
    dossier = relationship("DossierDB", back_populates="documents")
