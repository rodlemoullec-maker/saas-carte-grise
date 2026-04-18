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
    # Formulaires
    COC = "COC"
    CERFA_VN = "CERFA_VN"           # D-01 : 13749*06 demande CG VN
    CERFA_VO = "CERFA_VO"           # D-02 : 13750*07 demande CG VO
    CERFA_CESSION = "CERFA_CESSION" # D-03 : 15776*02 cession
    MANDAT = "MANDAT"               # D-04 : 13757*03 mandat
    DA = "DA"                       # D-05 : 13751*02 déclaration d'achat
    # Identité
    FACTURE = "FACTURE"
    CNI = "CNI"
    PASSEPORT = "PASSEPORT"
    PERMIS = "PERMIS"
    # Domicile
    DOMICILE = "DOMICILE"
    # Véhicule
    CG_BARREE = "CG_BARREE"         # D-17
    ASSURANCE = "ASSURANCE"         # D-19
    RECEPISEE_DA = "RECEPISEE_DA"   # D-21
    # Personne morale
    KBIS = "KBIS"                   # D-23
    # Attestations diverses
    ATTESTATION_FORMATION = "ATTESTATION_FORMATION"      # Formation 7h moto 125cc/L5e
    ATTESTATION_HEBERGEMENT = "ATTESTATION_HEBERGEMENT"  # Attestation manuscrite hebergement
    CNI_HEBERGEANT = "CNI_HEBERGEANT"                    # CNI de l'hebergeant
    CERTIFICAT_CESSION = "CERTIFICAT_CESSION"            # 15776 signe depose par le pro


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
    co2_wltp: float | None = None   # g/km — cycle WLTP (post-2021, base malus)
    co2_nedc: float | None = None   # g/km — cycle NEDC (pré-2021, legacy)
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
    departement_naissance: str | None = None  # Deduit de la commune (pour le Cerfa)
    sexe: str | None = None                   # M/F — deduit du prenom ou du passeport
    date_expiration: date
    date_delivrance: date | None = None       # Pour la regle CNI 2004-2013
    n_document: str
    nationalite: str | None = None
    mrz_ligne1: str | None = None
    mrz_ligne2: str | None = None
    mrz_valide: bool | None = None
    type_document: str  # CNI | PASSEPORT
    # Note : l'adresse sur la CNI/passeport n'est PAS extraite pour le Cerfa.
    # L'adresse du Cerfa vient du justificatif de domicile uniquement.
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
    lieu_naissance: str | None = None       # Pour croisement avec CNI
    n_permis: str
    categories: list[PermisCategorie] = Field(default_factory=list)
    categories_codes: list[str] = Field(default_factory=list)  # ["AM", "B1", "B"] — raccourci
    restrictions: list[str] = Field(default_factory=list)
    pays_emission: str = "France"
    date_delivrance: date | None = None
    date_expiration: date | None = None     # Champ 4b — validite du permis
    ocr_confidence: float = 0.0


class ExtractedAssurance(BaseModel):
    nom_assure: str
    prenom_assure: str
    vin: str | None = None
    immatriculation: str | None = None   # VO : immat au lieu du VIN
    marque: str | None = None
    modele: str | None = None
    n_contrat: str | None = None
    date_effet: date
    date_echeance: date
    compagnie: str | None = None
    garanties: list[str] = Field(default_factory=list)
    rc_incluse: bool = False
    provisoire: bool = False             # Attestation provisoire 1 mois
    memo_vehicule_assure: bool = False   # Mémo Véhicule Assuré 2025
    ocr_confidence: float = 0.0


# ─── Documents VO ─────────────────────────────────────────────────────────────


class ExtractedCGBarree(BaseModel):
    """D-17 — Carte grise barrée (VO)."""
    vin: str | None = None
    immatriculation: str | None = None
    n_formule: str | None = None        # Numéro de formule (11 chars)
    titulaire_nom: str | None = None
    titulaire_prenom: str | None = None
    date_vente: date | None = None      # "Vendu le" + date
    heure_vente: str | None = None      # Heure obligatoire (HH:MM)
    date_mise_circulation: date | None = None  # Champ B
    # Acheteur inscrit sur la barre horizontale
    acheteur_nom_barre: str | None = None
    acheteur_prenom_barre: str | None = None
    barre_diagonale: bool = False       # Barre diagonale détectée
    signatures_count: int = 0          # Nb de signatures détectées
    co_titulaires_count: int = 0       # Nb co-titulaires sur la CG
    # Champs techniques (pour le Cerfa)
    marque: str | None = None           # D.1
    genre_national: str | None = None   # J.1
    categorie_j: str | None = None      # J — categorie EU (L3e, M1, etc.)
    ocr_confidence: float = 0.0



class ExtractedDA(BaseModel):
    """D-05 — Déclaration d'achat pro."""
    vin: str | None = None
    immatriculation: str | None = None
    siren_pro: str | None = None
    siret_pro: str | None = None
    nom_pro: str | None = None
    date_achat: date | None = None
    vendeur_nom: str | None = None      # Titulaire de la CG cédée
    ocr_confidence: float = 0.0


class ExtractedRecepisseDA(BaseModel):
    """D-21 — Récépissé déclaration d'achat."""
    vin: str | None = None
    immatriculation: str | None = None
    siren_pro: str | None = None
    date_enregistrement: date | None = None
    ocr_confidence: float = 0.0


class ExtractedCerfa(BaseModel):
    """D-01/D-02 — Cerfa demande de CG (VN ou VO).

    Règles de signature (pro = toujours le vendeur) :
    - VN (13749) : aucune signature client requise, pro signe comme vendeur professionnel
    - VO (13750) : aucune signature client requise, pro signe comme vendeur professionnel
    - La signature client est requise UNIQUEMENT sur la cession 15776 (voir ExtractedCession)
    - Le cachet/signature du pro est apposé automatiquement après génération
    """
    type_cerfa: str | None = None       # "13749" ou "13750"
    vin: str | None = None
    immatriculation: str | None = None
    nom_titulaire: str | None = None
    prenoms_titulaire: str | None = None
    adresse: str | None = None
    code_postal: str | None = None
    ville: str | None = None
    puissance_fiscale_cv: int | None = None     # Case P.6 du Cerfa
    signe_pro: bool = False             # Signature/cachet pro (apposé auto)
    date_signature: date | None = None
    rature_detectee: bool = False
    n_formule_ancienne_cg: str | None = None  # VO uniquement
    ocr_confidence: float = 0.0


class ExtractedCession(BaseModel):
    """D-03 — Cerfa 15776 cession."""
    vin: str | None = None
    immatriculation: str | None = None
    vendeur_nom: str | None = None
    vendeur_siret: str | None = None
    acheteur_nom: str | None = None
    date_cession: date | None = None
    signatures_vendeur: bool = False
    signature_acheteur: bool = False
    tampon_siret: bool = False
    ocr_confidence: float = 0.0


class ExtractedKbis(BaseModel):
    """D-23 — Kbis / avis SIRENE."""
    raison_sociale: str | None = None
    siren: str | None = None
    siret_siege: str | None = None
    representant_nom: str | None = None
    representant_prenom: str | None = None
    adresse_siege: str | None = None
    date_kbis: date | None = None
    ocr_confidence: float = 0.0


class ExtractedMandat(BaseModel):
    """D-04 — Mandat de vente / procuration (Cerfa 13757)."""
    mandant_nom: str | None = None          # Nom du donneur de mandat (vendeur)
    mandant_prenom: str | None = None
    mandataire_nom: str | None = None       # Nom du mandataire (professionnel)
    mandataire_siret: str | None = None
    vin: str | None = None
    immatriculation: str | None = None
    date_mandat: date | None = None
    signature_mandant: bool = False
    ocr_confidence: float = 0.0


class ExtractedAttestationFormation(BaseModel):
    """ATTESTATION_FORMATION — Attestation de suivi de formation 7h (moto 125cc / L5e)."""
    nom_stagiaire: str | None = None
    prenom_stagiaire: str | None = None
    date_naissance: date | None = None
    organisme_formation: str | None = None
    date_formation: date | None = None
    duree_heures: int | None = None         # Doit être >= 7
    type_formation: str | None = None       # "125cc" ou "L5e" ou "moto"
    numero_attestation: str | None = None
    signature_organisme: bool = False
    ocr_confidence: float = 0.0


class ExtractedAttestationHebergement(BaseModel):
    """ATTESTATION_HEBERGEMENT — Attestation d'hébergement (manuscrite ou imprimée)."""
    hebergeant_nom: str | None = None
    hebergeant_prenom: str | None = None
    heberge_nom: str | None = None          # Nom de la personne hébergée
    heberge_prenom: str | None = None
    adresse_hebergement: str | None = None
    code_postal: str | None = None
    ville: str | None = None
    date_attestation: date | None = None
    signature_hebergeant: bool = False
    ocr_confidence: float = 0.0


class ExtractedCNIHebergeant(BaseModel):
    """CNI_HEBERGEANT — CNI de l'hébergeant (même structure que ExtractedIdentite)."""
    nom: str | None = None
    prenom: str | None = None
    date_naissance: date | None = None
    lieu_naissance: str | None = None
    numero_document: str | None = None
    date_expiration: date | None = None
    nationalite: str | None = None
    ocr_confidence: float = 0.0


class ExtractedCertificatCession(BaseModel):
    """CERTIFICAT_CESSION — Cerfa 15776 déposé/tamponné par le professionnel."""
    vin: str | None = None
    immatriculation: str | None = None
    vendeur_nom: str | None = None
    vendeur_siret: str | None = None
    acheteur_nom: str | None = None
    date_cession: date | None = None
    signatures_vendeur: bool = False
    signature_acheteur: bool = False
    tampon_pro: bool = False                # Cachet pro présent (différenciateur vs ExtractedCession)
    numero_cerfa: str | None = None        # "15776" attendu
    ocr_confidence: float = 0.0

