"""
Validateurs de qualité documentaire (V-20, V-21, V-22).

Ces validateurs vérifient la qualité technique des documents uploadés
avant l'extraction OCR. Ils s'appuient sur les métadonnées retournées
par le pipeline OCR (Document AI ou autre).

V-20 : Document illisible (score OCR < seuil)
V-21 : Scan tronqué (bords coupés)
V-22 : Langue étrangère détectée
"""
from __future__ import annotations

from dataclasses import dataclass

from engine.validators.base import BaseValidator, ValidationLevel, ValidationResult


# Seuils OCR
OCR_CONFIDENCE_BLOCKING = 0.40   # < 40% → illisible, scan inutilisable
OCR_CONFIDENCE_WARNING = 0.70    # < 70% → qualité insuffisante, erreurs probables
OCR_CONFIDENCE_GOOD = 0.85       # ≥ 85% → qualité acceptable

# Seuil de couverture page (% de la page utile détectée)
PAGE_COVERAGE_MIN = 0.80         # < 80% → probablement tronqué

# Langues acceptées pour les documents français
ACCEPTED_LANGUAGES = {"fr", "french"}
# Le COC peut être dans une autre langue EU — on accepte avec WARNING
COC_ACCEPTED_LANGUAGES = {"fr", "de", "en", "it", "es", "nl", "pt",
                          "french", "german", "english", "italian",
                          "spanish", "dutch", "portuguese"}


@dataclass
class DocumentQualityMetadata:
    """Métadonnées de qualité retournées par le pipeline OCR."""
    ocr_confidence: float                    # 0.0 – 1.0
    page_coverage: float = 1.0               # % de surface utile détectée (0.0 – 1.0)
    detected_language: str | None = None      # Code langue ISO ou nom
    is_coc: bool = False                      # Le COC peut être en langue étrangère
    has_blank_zones: bool = False             # Zones blanches suspectes détectées
    resolution_dpi: int | None = None         # Résolution image (si disponible)


class DocumentQualityValidator(BaseValidator):
    """
    Vérifie la qualité technique d'un document scanné/uploadé.

    Contrôles :
    - V-20 : Score OCR < seuil → document illisible
    - V-21 : Couverture page < 80% → scan tronqué
    - V-22 : Langue non française (sauf COC multilingue)
    """

    def validate(self, quality: DocumentQualityMetadata) -> ValidationResult:
        result = ValidationResult(valid=True)

        # V-20 : Lisibilité OCR
        if quality.ocr_confidence < OCR_CONFIDENCE_BLOCKING:
            result.add_error(
                code="V-20",
                message=(
                    f"Document illisible — score OCR {quality.ocr_confidence:.0%} "
                    f"(minimum requis : {OCR_CONFIDENCE_BLOCKING:.0%})"
                ),
                level=ValidationLevel.BLOCKING,
                field="ocr_confidence",
                value=f"{quality.ocr_confidence:.2f}",
                correction_action=(
                    "Re-scanner le document avec un meilleur éclairage, "
                    "en évitant les reflets et en s'assurant que le document est bien à plat"
                ),
            )
        elif quality.ocr_confidence < OCR_CONFIDENCE_WARNING:
            result.add_error(
                code="V-20",
                message=(
                    f"Qualité OCR insuffisante — score {quality.ocr_confidence:.0%} "
                    f"(recommandé ≥ {OCR_CONFIDENCE_GOOD:.0%}). "
                    "Des erreurs d'extraction sont probables."
                ),
                level=ValidationLevel.WARNING,
                field="ocr_confidence",
                value=f"{quality.ocr_confidence:.2f}",
                correction_action="Re-scanner le document pour améliorer la qualité si possible",
            )

        # Résolution trop basse
        if quality.resolution_dpi is not None and quality.resolution_dpi < 150:
            result.add_error(
                code="V-20",
                message=f"Résolution trop basse ({quality.resolution_dpi} DPI — minimum recommandé : 200 DPI)",
                level=ValidationLevel.WARNING,
                field="resolution_dpi",
                value=str(quality.resolution_dpi),
                correction_action="Re-scanner en 300 DPI minimum",
            )

        # V-21 : Scan tronqué
        if quality.page_coverage < PAGE_COVERAGE_MIN:
            result.add_error(
                code="V-21",
                message=(
                    f"Scan probablement tronqué — seulement {quality.page_coverage:.0%} "
                    f"de la surface utile détectée (minimum {PAGE_COVERAGE_MIN:.0%})"
                ),
                level=ValidationLevel.BLOCKING,
                field="page_coverage",
                value=f"{quality.page_coverage:.2f}",
                correction_action=(
                    "Re-scanner en s'assurant que l'intégralité du document "
                    "est visible (pas de bords coupés)"
                ),
            )

        if quality.has_blank_zones:
            result.add_error(
                code="V-21",
                message="Zones blanches suspectes détectées — possible document tronqué ou masqué",
                level=ValidationLevel.WARNING,
                field="blank_zones",
                correction_action="Vérifier que rien ne masque le document (doigt, post-it, reflet)",
            )

        # V-22 : Langue étrangère
        if quality.detected_language:
            lang = quality.detected_language.lower().strip()
            if quality.is_coc:
                # Le COC est souvent en allemand, anglais, etc.
                if lang not in COC_ACCEPTED_LANGUAGES:
                    result.add_error(
                        code="V-22",
                        message=(
                            f"COC en langue non reconnue ({quality.detected_language}) — "
                            "une traduction assermentée peut être requise"
                        ),
                        level=ValidationLevel.WARNING,
                        field="langue",
                        value=quality.detected_language,
                    )
            else:
                if lang not in ACCEPTED_LANGUAGES:
                    result.add_error(
                        code="V-22",
                        message=(
                            f"Document en langue étrangère ({quality.detected_language}) — "
                            "une traduction assermentée en français est obligatoire"
                        ),
                        level=ValidationLevel.BLOCKING,
                        field="langue",
                        value=quality.detected_language,
                        correction_action=(
                            "Fournir une traduction assermentée du document "
                            "par un traducteur agréé auprès d'un tribunal français"
                        ),
                    )

        return result
