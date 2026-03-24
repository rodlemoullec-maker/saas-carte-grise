"""
Modèles de données pour les documents soumis dans un dossier.

Chaque type de document a son propre schéma d'extraction (ExtractedXxx).
Ces modèles représentent les données après OCR + extraction structurée.

TODO: enrichir les schémas au fur et à mesure des cas terrain.
"""
from __future__ import annotations

import uuid
from datetime import date, datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class DocumentType(str, Enum):
    COC = "COC"
    FACTURE = "FACTURE"
    CNI = "CNI"
    PASSEPORT = "PASSEPORT"
    TITRE_SEJOUR = "TITRE_SEJOUR"
    DOMICILE = "DOMICILE"
    PERMIS = "PERMIS"
    ASSURANCE = "ASSURANCE"
    KBIS = "KBIS"


class DocumentStatus(str, Enum):
    PENDING = "PENDING"
    PROCESSING = "PROCESSING"
    EXTRACTED = "EXTRACTED"
    VALIDATED = "VALIDATED"
    REJECTED = "REJECTED"


class Document(BaseModel):
    id: uuid.UUID = Field(default_factory=uuid.uuid4)
    dossier_id: uuid.UUID
    type: DocumentType
    status: DocumentStatus = DocumentStatus.PENDING

    file_path: str
    file_hash: str | None = None
    file_size: int | None = None
    mime_type: str | None = None
    page_count: int | None = None

    ocr_confidence: float | None = None
    extracted_data: dict[str, Any] | None = None
    validation_result: dict[str, Any] | None = None

    uploaded_at: datetime = Field(default_factory=datetime.utcnow)
    processed_at: datetime | None = None


# ─── Schémas d'extraction structurée ─────────────────────────────────────────

class ExtractedCOC(BaseModel):
    vin: str
    cnit: str | None = None
    marque: str
    modele: str | None = None
    energie: str
    carrosserie: str | None = None
    puissance_kw: float | None = None
    puissance_fiscale_cv: int | None = None
    cylindree_cm3: int | None = None
    places_assises: int | None = None
    ptac_kg: int | None = None
    n_homologation_eu: str | None = None
    constructeur: str | None = None
    date_premiere_immat_ue: date | None = None
    ocr_confidence: float = 0.0


class ExtractedFacture(BaseModel):
    vin: str
    marque: str
    modele: str | None = None
    energie: str | None = None
    date_vente: date
    prix_ht: float | None = None
    prix_ttc: float | None = None
    tva_taux: float | None = None
    siret_vendeur: str
    nom_vendeur: str
    adresse_vendeur: str | None = None
    nom_acheteur: str
    adresse_acheteur: str | None = None
    n_facture: str | None = None
    kilometrage: int | None = None
    mention_neuf: bool = False
    ocr_confidence: float = 0.0


class ExtractedIdentite(BaseModel):
    nom_naissance: str
    nom_usage: str | None = None
    prenoms: list[str] = Field(default_factory=list)
    date_naissance: date
    lieu_naissance: str | None = None
    date_expiration: date
    n_document: str
    nationalite: str | None = None
    mrz_ligne1: str | None = None
    mrz_ligne2: str | None = None
    mrz_valide: bool | None = None
    type_document: str  # CNI | PASSEPORT | TITRE_SEJOUR
    ocr_confidence: float = 0.0


class ExtractedDomicile(BaseModel):
    nom_titulaire: str
    adresse_ligne1: str
    adresse_ligne2: str | None = None
    code_postal: str
    ville: str
    pays: str = "France"
    date_document: date
    type_justificatif: str | None = None
    emetteur: str | None = None
    ban_normalized: dict[str, Any] | None = None
    ocr_confidence: float = 0.0


class PermisCategorie(BaseModel):
    code: str
    date_obtention: date | None = None
    date_validite: date | None = None


class ExtractedPermis(BaseModel):
    nom: str
    prenom: str
    date_naissance: date
    n_permis: str
    categories: list[PermisCategorie] = Field(default_factory=list)
    restrictions: list[str] = Field(default_factory=list)
    pays_emission: str = "France"
    date_delivrance: date | None = None
    ocr_confidence: float = 0.0


class ExtractedAssurance(BaseModel):
    nom_assure: str
    prenom_assure: str
    vin: str | None = None
    marque: str | None = None
    modele: str | None = None
    n_contrat: str | None = None
    date_effet: date
    date_echeance: date
    compagnie: str | None = None
    garanties: list[str] = Field(default_factory=list)
    rc_incluse: bool = False
    provisoire: bool = False
    ocr_confidence: float = 0.0
