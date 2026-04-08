"""
Modèle Document — un fichier uploadé dans un dossier.

Version locale : storage_path pointe vers un fichier chiffré sur le disque
local de l'agent. Aucune dépendance à un stockage cloud.
"""
from __future__ import annotations

import uuid

from sqlalchemy import JSON, Boolean, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from api.models.base import Base, TimestampMixin


class DocumentDB(Base, TimestampMixin):
    __tablename__ = "documents"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))

    dossier_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("dossiers.id", ondelete="CASCADE"), index=True,
    )

    # Type et statut
    type: Mapped[str] = mapped_column(String(40))  # DocumentType enum value
    status: Mapped[str] = mapped_column(String(20), default="PENDING")

    # Fichier (stockage local chiffré)
    storage_path: Mapped[str] = mapped_column(String(500))
    original_filename: Mapped[str] = mapped_column(String(255))
    mime_type: Mapped[str] = mapped_column(String(100))
    file_size_bytes: Mapped[int] = mapped_column(Integer)
    sha256: Mapped[str] = mapped_column(String(64))  # Intégrité + dédoublonnage

    # Provenance : drag & drop email ou import direct
    source_email_subject: Mapped[str | None] = mapped_column(String(500), nullable=True)
    source_email_from: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # OCR
    ocr_provider: Mapped[str | None] = mapped_column(String(50), nullable=True)
    ocr_confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    ocr_raw_text: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Extraction structurée (résultat OCR → modèle Pydantic sérialisé)
    extracted_data: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    # Validation individuelle
    validation_result: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    # Qualité
    page_coverage: Mapped[float | None] = mapped_column(Float, nullable=True)
    detected_language: Mapped[str | None] = mapped_column(String(10), nullable=True)

    # Classifié automatiquement ?
    auto_classified: Mapped[bool] = mapped_column(Boolean, default=False)
    classification_confidence: Mapped[float | None] = mapped_column(Float, nullable=True)

    # Relation
    dossier = relationship("DossierDB", back_populates="documents")
