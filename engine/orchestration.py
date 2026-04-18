"""
Orchestration intelligente de la détection et extraction de documents.

Ce module fournit une couche unifiée qui :
1. Détecte le type de document par heuristique
2. Instancie l'extracteur approprié
3. Retourne les résultats structurés (ExtractionResult)

Remplace progressivement la logique manuelle dans engine/pipeline/realtime.py
"""
from __future__ import annotations

import logging
import re
from typing import Any

from engine.extractors import (
    AssuranceExtractor,
    AttestationFormationExtractor,
    AttestationHebergementExtractor,
    BaseExtractor,
    CertificatCessionExtractor,
    CessionExtractor,
    CGBarreeExtractor,
    CNIHebergeantExtractor,
    COCExtractor,
    DAExtractor,
    DomicileExtractor,
    ExtractionResult,
    FactureExtractor,
    IdentiteExtractor,
    KbisExtractor,
    MandatExtractor,
    PermisExtractor,
    RecepissedaExtractor,
)
from engine.models.documents import DocumentType

logger = logging.getLogger(__name__)


# ── Heuristiques de détection (mots-clés + patterns) ────────────────────────────

DETECTION_PATTERNS: dict[DocumentType, list[tuple[str, float]]] = {
    # Priorités hautes (patterns très spécifiques)
    DocumentType.COC: [
        (r"certificat.*conformit|c\.o\.c|cerfa.*3196", 1.0),
        (r"cnit.*identification", 0.9),
        (r"puissance.*fiscale|marque.*modèle.*vin", 0.7),
    ],
    DocumentType.CERFA_CESSION: [
        (r"certificat.*cession|cerfa.*15\s*776|15776", 1.0),
        (r"cession.*véhicule|déclaration.*cession", 0.85),
    ],
    DocumentType.MANDAT: [
        (r"mandat.*vente|cerfa.*13757|13757.*mandat", 1.0),
        (r"procuration.*véhicule|pouvoir.*vente", 0.8),
    ],
    DocumentType.DA: [
        (r"déclaration.*achat|cerfa.*13751|13751.*déclaration", 1.0),
        (r"d\.a\.|décl.*achat", 0.75),
    ],
    DocumentType.RECEPISEE_DA: [
        (r"récépissé.*déclaration.*achat|recepisse.*da", 1.0),
        (r"récépissé.*enregistr", 0.8),
    ],
    DocumentType.CG_BARREE: [
        (r"carte.*grise.*barr|cg.*barr|vendu\s*le", 1.0),
        (r"certificat.*immatricul.*barr|barre.*diagon", 0.85),
    ],
    DocumentType.KBIS: [
        (r"extrait.*registre.*commerce|kbis|avis\s*sirene", 1.0),
        (r"sirene.*siren.*siret", 0.75),
    ],
    DocumentType.ATTESTATION_FORMATION: [
        (r"attestation.*formation|formation.*moto", 0.95),
        (r"125\s*cm[³3°º]|l5e|conduite.*moto|formation.*7", 0.75),
    ],
    DocumentType.ATTESTATION_HEBERGEMENT: [
        (r"attestation.*hébergement|je\s*soussigné.*héberg", 1.0),
        (r"hébergé.*domicil|domicil.*chez", 0.75),
    ],
    DocumentType.CNI_HEBERGEANT: [
        (r"carte.*identité.*hébergeant|cni.*héberg", 0.9),
        (r"(?:CNI|passeport).*hébergeant|hébergeant.*identité", 0.8),
    ],
    DocumentType.CERTIFICAT_CESSION: [
        (r"certificat.*cession.*tampon|cession.*tampon.*pro|15776.*tampon", 1.0),
        (r"cession.*cachet.*professionnel", 0.85),
    ],
    # Identité
    DocumentType.CNI: [
        (r"carte\s*nationale\s*d['\u2019]identité|c\.n\.i\.|carte\s*d['\u2019]identité", 1.0),
        (r"republique\s*française", 0.5),
    ],
    DocumentType.PASSEPORT: [
        (r"passeport|passport", 1.0),
        (r"machine\s*readable|<{2}", 0.7),
    ],
    DocumentType.PERMIS: [
        (r"permis\s*(?:de\s*)?conduire|driving\s*licence|catégorie|signé\s*le", 1.0),
        (r"n[°º]?\s*permis", 0.75),
    ],
    # Véhicule
    DocumentType.FACTURE: [
        (r"facture.*(?:achat|vente).*véhicule|bon.*livraison.*auto|numéro.*facture", 0.9),
        (r"vin\s*:|prix.*ttc|facture", 0.6),
    ],
    DocumentType.COC: [
        (r"certificat.*conformité", 1.0),
    ],
    DocumentType.ASSURANCE: [
        (r"attestation.*assurance|certificat.*assurance|contrat.*automobile", 1.0),
        (r"assuré|numéro.*police|tiers.*responsabil", 0.7),
    ],
    # Domicile
    DocumentType.DOMICILE: [
        (r"edf|électric|facture.*internet|relevé.*bancaire|avis.*imposition|hébergement", 0.8),
        (r"adresse|titulaire|consommat", 0.4),
    ],
}


class DocumentOrchestrator:
    """Orchestrateur central pour la détection et extraction automatiques."""

    def __init__(self):
        """Initialise les extracteurs (instanciés une seule fois)."""
        self.extractors: dict[DocumentType, BaseExtractor] = {
            DocumentType.COC: COCExtractor(),
            DocumentType.CERFA_CESSION: CessionExtractor(),
            DocumentType.MANDAT: MandatExtractor(),
            DocumentType.DA: DAExtractor(),
            DocumentType.RECEPISEE_DA: RecepissedaExtractor(),
            DocumentType.CG_BARREE: CGBarreeExtractor(),
            DocumentType.KBIS: KbisExtractor(),
            DocumentType.ATTESTATION_FORMATION: AttestationFormationExtractor(),
            DocumentType.ATTESTATION_HEBERGEMENT: AttestationHebergementExtractor(),
            DocumentType.CNI_HEBERGEANT: CNIHebergeantExtractor(),
            DocumentType.CERTIFICAT_CESSION: CertificatCessionExtractor(),
            DocumentType.CNI: IdentiteExtractor(),  # partage identite
            DocumentType.PASSEPORT: IdentiteExtractor(),  # partage identite
            DocumentType.PERMIS: PermisExtractor(),
            DocumentType.FACTURE: FactureExtractor(),
            DocumentType.ASSURANCE: AssuranceExtractor(),
            DocumentType.DOMICILE: DomicileExtractor(),
        }

    def detect_document_type(self, ocr_text: str, confidence_threshold: float = 0.5) -> tuple[DocumentType | None, float]:
        """
        Détecte le type de document par heuristique (patterns + mots-clés).

        Args:
            ocr_text: Texte OCR brut du document
            confidence_threshold: Seuil minimum de confiance de détection

        Returns:
            (DocumentType détecté, score de confiance)
        """
        text_lower = ocr_text.lower()
        scores: dict[DocumentType, float] = {}

        for doc_type, patterns in DETECTION_PATTERNS.items():
            max_score = 0.0
            for pattern, weight in patterns:
                if re.search(pattern, text_lower, re.IGNORECASE):
                    max_score = max(max_score, weight)
            if max_score > 0:
                scores[doc_type] = max_score

        if not scores:
            return None, 0.0

        best_type = max(scores, key=scores.get)
        best_score = scores[best_type]

        if best_score >= confidence_threshold:
            return best_type, best_score

        return None, best_score

    def extract(
        self, ocr_text: str, detected_type: DocumentType | None = None
    ) -> ExtractionResult:
        """
        Détecte (si nécessaire) et extrait les données du document.

        Args:
            ocr_text: Texte OCR brut
            detected_type: Type optionnellement forcé (pour les tests ou quand connu)

        Returns:
            ExtractionResult avec success, data, confidence, errors
        """
        # Détection si non fourni
        if detected_type is None:
            detected_type, _ = self.detect_document_type(ocr_text)

        if detected_type is None:
            logger.warning("Document type not detected")
            return ExtractionResult(
                success=False,
                data=None,
                confidence=0.0,
                errors=["Document type not detected"],
            )

        # Récupère l'extracteur
        extractor = self.extractors.get(detected_type)
        if extractor is None:
            logger.error(f"No extractor for type {detected_type}")
            return ExtractionResult(
                success=False,
                data=None,
                confidence=0.0,
                errors=[f"No extractor for type {detected_type}"],
            )

        # Extraction
        try:
            result = extractor.extract(ocr_text)
            # Ajoute le type détecté aux métadonnées
            if result.data:
                result.data["__document_type"] = detected_type.value
            return result
        except Exception as e:
            logger.error(f"[{detected_type}] Extraction failed: {e}", exc_info=True)
            return ExtractionResult(
                success=False,
                data=None,
                confidence=0.0,
                errors=[str(e)],
            )

    def extract_with_fallback(self, ocr_text: str) -> dict[str, Any]:
        """
        Wrapper compatible avec l'ancien API (retourne dict au lieu d'ExtractionResult).

        Utilisé par les routers pour la rétro-compatibilité.

        Returns:
            {
                "success": bool,
                "data": dict,
                "confidence": float,
                "errors": list,
                "document_type": str
            }
        """
        # Détection en amont pour inclure le type même en cas d'échec d'extraction
        detected_type, _ = self.detect_document_type(ocr_text)
        result = self.extract(ocr_text, detected_type=detected_type)
        doc_type_value = (
            detected_type.value if detected_type else
            (result.data.get("__document_type") if result.data else None)
        )
        return {
            "success": result.success,
            "data": result.data or {},
            "confidence": result.confidence,
            "errors": result.errors,
            "document_type": doc_type_value,
        }


# Instance globale (singleton)
_orchestrator: DocumentOrchestrator | None = None


def get_orchestrator() -> DocumentOrchestrator:
    """Retourne l'instance singleton de l'orchestrateur."""
    global _orchestrator
    if _orchestrator is None:
        _orchestrator = DocumentOrchestrator()
    return _orchestrator


def detect_and_extract(ocr_text: str, document_type: str | None = None) -> dict[str, Any]:
    """
    Fonction publique de détection + extraction (API publique).

    Args:
        ocr_text: Texte OCR brut
        document_type: Type optionnel (si connu)

    Returns:
        Dict avec success, data, confidence, errors, document_type
    """
    orchestrator = get_orchestrator()
    if document_type:
        try:
            doc_type_enum = DocumentType(document_type)
        except ValueError:
            logger.warning(f"Invalid document type: {document_type}")
            doc_type_enum = None
    else:
        doc_type_enum = None

    result = orchestrator.extract(ocr_text, doc_type_enum)
    return {
        "success": result.success,
        "data": result.data or {},
        "confidence": result.confidence,
        "errors": result.errors,
        "document_type": result.data.get("__document_type") if result.data else None,
    }
