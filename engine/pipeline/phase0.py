"""
Pipeline Phase 0 — Pré-diagnostic gratuit (VO uniquement).

Consultation automatique HistoVec/CSA dès la saisie de l'immatriculation.
Détecte gage, OTCI, vol, VEC/VEI AVANT tout coût pour le pro.

Entrée : immatriculation (ou VIN)
Sortie : Phase0Result avec statuts SIV + avis GO/STOP
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum

from engine.cross_checks.siv_status import (
    GageCheck,
    OTCICheck,
    VECVEICheck,
    VolSignaleCheck,
)
from engine.models.decision import CrossCheckResult, CrossCheckStatus
from engine.models.documents import ExtractedHistoVec


class Phase0Verdict(str, Enum):
    GO = "GO"           # Aucun blocage SIV — le pro peut continuer
    STOP = "STOP"       # Blocage SIV détecté — arrêt immédiat
    WARNING = "WARNING" # Situation à risque mais pas bloquante (VEC)


@dataclass
class Phase0Result:
    verdict: Phase0Verdict
    cross_check_results: list[CrossCheckResult] = field(default_factory=list)
    blockers: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


class Phase0Pipeline:
    """
    Pipeline Phase 0 — gratuit, exécuté dès la saisie de l'immat.

    Usage:
        histovec = await histovec_client.fetch(immatriculation)
        result = Phase0Pipeline().run(histovec)
        if result.verdict == Phase0Verdict.STOP:
            notify_pro("Véhicule bloqué", result.blockers)
    """

    def run(self, histovec: ExtractedHistoVec) -> Phase0Result:
        all_results: list[CrossCheckResult] = []
        blockers: list[str] = []
        warnings: list[str] = []

        # C-20 : Vol — check en premier (le plus critique)
        vol_results = VolSignaleCheck().run(histovec)
        all_results.extend(vol_results)
        for r in vol_results:
            if r.status == CrossCheckStatus.FAIL:
                blockers.append(r.detail or "Vol signalé")

        # C-17 : Gage
        gage_results = GageCheck().run(histovec)
        all_results.extend(gage_results)
        for r in gage_results:
            if r.status == CrossCheckStatus.FAIL:
                blockers.append(r.detail or "Gage actif")

        # C-18 : OTCI
        otci_results = OTCICheck().run(histovec)
        all_results.extend(otci_results)
        for r in otci_results:
            if r.status == CrossCheckStatus.FAIL:
                blockers.append(r.detail or "OTCI active")

        # C-19 : VEC/VEI
        vecvei_results = VECVEICheck().run(histovec)
        all_results.extend(vecvei_results)
        for r in vecvei_results:
            if r.status == CrossCheckStatus.FAIL:
                if "VEI" in (r.detail or ""):
                    blockers.append(r.detail or "VEI — destruction")
                else:
                    warnings.append(r.detail or "VEC — réparation requise")

        # Kilométrage dernier CT (informatif)
        if histovec.km_dernier_ct is not None and histovec.km_dernier_ct > 0:
            warnings.append(f"Kilométrage dernier CT : {histovec.km_dernier_ct:,} km")

        # Verdict
        if blockers:
            verdict = Phase0Verdict.STOP
        elif warnings:
            verdict = Phase0Verdict.WARNING
        else:
            verdict = Phase0Verdict.GO

        return Phase0Result(
            verdict=verdict,
            cross_check_results=all_results,
            blockers=blockers,
            warnings=warnings,
        )
