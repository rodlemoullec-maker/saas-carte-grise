"""
Moteur de decision principal.

Logique binaire — pas de score pondere.
Un dossier est soit conforme (VERT), soit avec warnings (ORANGE), soit bloque (ROUGE).

ROUGE  = au moins 1 verrouillage V-XX declenche
ORANGE = zero verrouillage, au moins 1 warning
VERT   = zero verrouillage, zero warning
"""
from __future__ import annotations

from engine.decision.rules import BLOCKING_RULES, get_triggered_blocking_rules
from engine.models.decision import (
    CrossCheckResult,
    CrossCheckStatus,
    Decision,
    DecisionStatus,
    Diagnostic,
)


class DecisionEngine:

    def decide(
        self,
        cross_check_results: list[CrossCheckResult],
        validation_errors: list | None = None,
        extra_blocking_rules: list[str] | None = None,
    ) -> Decision:
        """
        Point d'entree du moteur de decision.

        1. Collecter tous les blocages (V-XX) depuis cross-checks + validations
        2. Collecter tous les warnings
        3. Detecter la fraude
        4. Produire le diagnostic VERT / ORANGE / ROUGE
        """
        validation_errors = validation_errors or []

        # ─── Collecter les blocages ───────────────────────────────────────
        blocages = list(extra_blocking_rules or [])
        blocages += get_triggered_blocking_rules(cross_check_results)

        for error in validation_errors:
            if hasattr(error, "code") and error.code in BLOCKING_RULES:
                blocages.append(error.code)

        blocages = list(set(blocages))

        # ─── Collecter les warnings ───────────────────────────────────────
        warnings = []
        for r in cross_check_results:
            if r.status == CrossCheckStatus.WARNING and r.detail:
                warnings.append(r.detail)

        # ─── Fraude ───────────────────────────────────────────────────────
        fraud_indicators = [
            code for code in blocages
            if code in BLOCKING_RULES and BLOCKING_RULES[code].is_fraud_related
        ]

        if fraud_indicators:
            return Decision(
                diagnostic=Diagnostic.ROUGE,
                status=DecisionStatus.FRAUDE,
                blocages=blocages,
                warnings=warnings,
                cross_check_results=cross_check_results,
                fraud_indicators=fraud_indicators,
                requires_human_review=True,
            )

        # ─── Diagnostic binaire ───────────────────────────────────────────
        if blocages:
            return Decision(
                diagnostic=Diagnostic.ROUGE,
                status=DecisionStatus.CORRECTION,
                blocages=blocages,
                warnings=warnings,
                cross_check_results=cross_check_results,
            )

        if warnings:
            return Decision(
                diagnostic=Diagnostic.ORANGE,
                status=DecisionStatus.REVUE_AGENT,
                blocages=[],
                warnings=warnings,
                cross_check_results=cross_check_results,
                requires_human_review=True,
            )

        return Decision(
            diagnostic=Diagnostic.VERT,
            status=DecisionStatus.ACCEPTE,
            blocages=[],
            warnings=[],
            cross_check_results=cross_check_results,
        )
