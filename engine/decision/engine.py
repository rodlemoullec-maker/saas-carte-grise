"""
Moteur de décision principal.

Orchestre : règles bloquantes → scoring → statut final.
"""
from __future__ import annotations

from engine.decision.rules import BLOCKING_RULES, get_triggered_blocking_rules
from engine.decision.scoring import compute_score
from engine.models.decision import Decision, DecisionStatus


# Seuils de décision
THRESHOLD_ACCEPT = 95.0
THRESHOLD_CORRECTION = 60.0


class DecisionEngine:

    def decide(
        self,
        cross_check_results: list,
        validation_errors: list,
        extra_blocking_rules: list[str] | None = None,
    ) -> Decision:
        """
        Point d'entrée principal du moteur de décision.

        Étapes :
        1. Vérification des règles bloquantes (court-circuit)
        2. Calcul du score global
        3. Détermination du statut final
        """
        all_blocking = list(extra_blocking_rules or [])
        all_blocking += get_triggered_blocking_rules(cross_check_results)

        # Règles bloquantes issues des validations individuelles
        for error in validation_errors:
            if hasattr(error, "code") and error.code in BLOCKING_RULES:
                all_blocking.append(error.code)

        all_blocking = list(set(all_blocking))

        # Fraude détectée ?
        fraud_indicators = [
            r for r in all_blocking
            if r in BLOCKING_RULES and BLOCKING_RULES[r].is_fraud_related
        ]

        if fraud_indicators:
            return Decision(
                status=DecisionStatus.FRAUDE,
                score=0.0,
                cross_check_results=cross_check_results,
                blocking_rules_triggered=all_blocking,
                fraud_indicators=fraud_indicators,
                requires_human_review=True,
            )

        # Règle bloquante non-fraude
        if all_blocking:
            return Decision(
                status=DecisionStatus.REJET,
                score=0.0,
                cross_check_results=cross_check_results,
                blocking_rules_triggered=all_blocking,
                requires_human_review=False,
            )

        # Calcul du score
        score = compute_score(cross_check_results)

        if score >= THRESHOLD_ACCEPT:
            return Decision(
                status=DecisionStatus.ACCEPTE,
                score=score,
                cross_check_results=cross_check_results,
            )
        elif score >= THRESHOLD_CORRECTION:
            return Decision(
                status=DecisionStatus.REVUE_AGENT,
                score=score,
                cross_check_results=cross_check_results,
                requires_human_review=True,
            )
        else:
            return Decision(
                status=DecisionStatus.REJET,
                score=score,
                cross_check_results=cross_check_results,
            )
