"""
Cross-checks sur le statut SIV / HistoVec du véhicule.

Règles implémentées :
  C-17 — Gage actif → blocage vente
  C-18 — OTCI (Opposition au Transfert de Carte Grise) active → blocage
  C-19 — VEC / VEI → blocage (véhicule économiquement compromis/irréparable)
  C-20 — Vol signalé → blocage immédiat + alerte fraude
  C-21 — Doublon VIN interne (VIN déjà enregistré dans notre système)
"""
from __future__ import annotations

from engine.cross_checks.base import BaseCrossCheck
from engine.models.decision import CrossCheckResult, CrossCheckStatus
from engine.models.documents import ExtractedHistoVec


class GageCheck(BaseCrossCheck):
    """C-17 — Vérifie qu'aucun gage n'est actif sur le véhicule."""

    @property
    def name(self) -> str:
        return "gage_check"

    def run(self, histovec: ExtractedHistoVec) -> list[CrossCheckResult]:
        if not histovec.gage_actif:
            return [CrossCheckResult(
                rule_name="gage_actif",
                status=CrossCheckStatus.PASS,
                source_a="CSA_HISTOVEC", source_b="SYSTEM",
                field="gage_actif",
                value_a="False", value_b="False",
                confidence=1.0,
            )]
        return [CrossCheckResult(
            rule_name="gage_actif",
            status=CrossCheckStatus.FAIL,
            source_a="CSA_HISTOVEC", source_b="SYSTEM",
            field="gage_actif",
            value_a="True", value_b="False",
            confidence=0.0,
            detail=(
                "Gage actif sur le véhicule — la vente est bloquée jusqu'à la levée du gage. "
                "Le vendeur doit contacter son créancier (banque/organisme de crédit)."
            ),
        )]


class OTCICheck(BaseCrossCheck):
    """C-18 — Vérifie l'absence d'opposition au transfert de carte grise."""

    @property
    def name(self) -> str:
        return "otci_check"

    def run(self, histovec: ExtractedHistoVec) -> list[CrossCheckResult]:
        if not histovec.otci_active:
            return [CrossCheckResult(
                rule_name="otci_active",
                status=CrossCheckStatus.PASS,
                source_a="CSA_HISTOVEC", source_b="SYSTEM",
                field="otci_active",
                value_a="False", value_b="False",
                confidence=1.0,
            )]
        return [CrossCheckResult(
            rule_name="otci_active",
            status=CrossCheckStatus.FAIL,
            source_a="CSA_HISTOVEC", source_b="SYSTEM",
            field="otci_active",
            value_a="True", value_b="False",
            confidence=0.0,
            detail=(
                "Opposition au Transfert de Carte Grise (OTCI) active — "
                "transfert de propriété impossible. Contacter les services compétents "
                "(tribunal, huissier) pour lever l'opposition."
            ),
        )]


class VECVEICheck(BaseCrossCheck):
    """C-19 — Vérifie que le véhicule n'est pas classé VEC ou VEI."""

    @property
    def name(self) -> str:
        return "vec_vei_check"

    def run(self, histovec: ExtractedHistoVec) -> list[CrossCheckResult]:
        results = []

        if histovec.vec:
            results.append(CrossCheckResult(
                rule_name="vec_status",
                status=CrossCheckStatus.FAIL,
                source_a="CSA_HISTOVEC", source_b="SYSTEM",
                field="vec",
                value_a="True", value_b="False",
                confidence=0.0,
                detail=(
                    "Véhicule Économiquement Compromis (VEC) — réparation obligatoire "
                    "et expertise avant toute remise en circulation. "
                    "Dossier bloqué jusqu'à levée du statut VEC."
                ),
            ))

        if histovec.vei:
            results.append(CrossCheckResult(
                rule_name="vei_status",
                status=CrossCheckStatus.FAIL,
                source_a="CSA_HISTOVEC", source_b="SYSTEM",
                field="vei",
                value_a="True", value_b="False",
                confidence=0.0,
                detail=(
                    "Véhicule Économiquement Irréparable (VEI) — véhicule destiné à la "
                    "destruction. Immatriculation impossible. Dossier rejeté définitivement."
                ),
            ))

        if not results:
            results.append(CrossCheckResult(
                rule_name="vec_vei_status",
                status=CrossCheckStatus.PASS,
                source_a="CSA_HISTOVEC", source_b="SYSTEM",
                field="vec_vei",
                value_a="False", value_b="False",
                confidence=1.0,
            ))

        return results


class VolSignaleCheck(BaseCrossCheck):
    """
    C-20 — Vérifie qu'aucun vol n'est signalé sur le véhicule.

    Un vol signalé déclenche une alerte fraude maximale — le dossier est
    immédiatement rejeté et transmis pour investigation.
    """

    @property
    def name(self) -> str:
        return "vol_signale_check"

    def run(self, histovec: ExtractedHistoVec) -> list[CrossCheckResult]:
        if not histovec.vol_signale:
            return [CrossCheckResult(
                rule_name="vol_signale",
                status=CrossCheckStatus.PASS,
                source_a="CSA_HISTOVEC", source_b="SYSTEM",
                field="vol_signale",
                value_a="False", value_b="False",
                confidence=1.0,
            )]
        return [CrossCheckResult(
            rule_name="vol_signale",
            status=CrossCheckStatus.FAIL,
            source_a="CSA_HISTOVEC", source_b="SYSTEM",
            field="vol_signale",
            value_a="True", value_b="False",
            confidence=0.0,
            detail=(
                "ALERTE FRAUDE — Véhicule signalé volé dans la base nationale. "
                "Dossier bloqué et transmis immédiatement au service de contrôle. "
                "Ne pas remettre le véhicule — contacter les autorités."
            ),
        )]


class DoublonVINCheck(BaseCrossCheck):
    """
    C-21 — Vérifie que le VIN n'est pas déjà associé à un dossier actif
    dans notre système (doublon interne).

    Le registre interne est passé en paramètre pour éviter tout couplage
    fort avec la couche base de données.
    """

    @property
    def name(self) -> str:
        return "doublon_vin_check"

    def run(
        self,
        vin: str,
        existing_dossier_ids: list[str],
        current_dossier_id: str | None = None,
    ) -> list[CrossCheckResult]:
        """
        Parameters
        ----------
        vin:
            Le VIN à vérifier.
        existing_dossier_ids:
            Liste des dossier_id déjà existants dans le système pour ce VIN
            (requête pré-chargée par le pipeline).
        current_dossier_id:
            Identifiant du dossier en cours — exclu de la comparaison.
        """
        doublons = [
            d for d in existing_dossier_ids
            if d != current_dossier_id
        ]

        if not doublons:
            return [CrossCheckResult(
                rule_name="doublon_vin_interne",
                status=CrossCheckStatus.PASS,
                source_a="SYSTEM", source_b="SYSTEM",
                field="vin",
                value_a=vin, value_b="",
                confidence=1.0,
            )]

        return [CrossCheckResult(
            rule_name="doublon_vin_interne",
            status=CrossCheckStatus.FAIL,
            source_a="SYSTEM", source_b="SYSTEM",
            field="vin",
            value_a=vin,
            value_b=", ".join(doublons),
            confidence=0.0,
            detail=(
                f"VIN {vin!r} déjà présent dans {len(doublons)} dossier(s) actif(s) : "
                f"{', '.join(doublons[:3])}{'...' if len(doublons) > 3 else ''}. "
                "Vérifier qu'il ne s'agit pas d'une double soumission."
            ),
        )]
