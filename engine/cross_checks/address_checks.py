"""
Cross-checks cohérence d'adresse entre documents.

Règles implémentées :
  C-04 — Adresse Cerfa ↔ justificatif de domicile
  C-05 — Adresse Cerfa ↔ titre de séjour (ressortissants étrangers)

Logique de comparaison :
  - Exact match (après normalisation) → PASS
  - Code postal identique + ville similaire → WARNING (adresse partielle)
  - Code postal différent → FAIL

L'appel BAN (normalisation géocodage) est délégué à integrations/ban_addresses.py
et n'est pas encore câblé ici (TODO) — on fonctionne en mode synchrone normalisé.
"""
from __future__ import annotations

import re
import unicodedata

from engine.cross_checks.base import BaseCrossCheck
from engine.models.decision import CrossCheckResult, CrossCheckStatus
from engine.models.documents import ExtractedCerfa, ExtractedDomicile, ExtractedIdentite


def _normalize_address_component(value: str) -> str:
    """Normalise un composant d'adresse : minuscule, sans accents, sans ponctuation."""
    value = unicodedata.normalize("NFKD", value)
    value = "".join(c for c in value if not unicodedata.combining(c))
    value = value.lower()
    value = re.sub(r"[,\.\-']", " ", value)
    value = re.sub(r"\b(rue|avenue|boulevard|bd|av|all[ée]e|impasse|sq|square|"
                   r"place|chemin|route|voie|hameau|lieu[- ]dit|lotissement|"
                   r"residence|r[eé]sidence|bat|b[âa]timent|immeuble)\b", "", value)
    value = re.sub(r"\s+", " ", value).strip()
    return value


def _normalize_city(value: str) -> str:
    value = unicodedata.normalize("NFKD", value)
    value = "".join(c for c in value if not unicodedata.combining(c))
    value = value.lower()
    value = re.sub(r"[,\.\-']", " ", value)
    value = re.sub(r"\s+", " ", value).strip()
    return value


def _compare_addresses(
    cerfa_adresse: str | None,
    cerfa_cp: str | None,
    cerfa_ville: str | None,
    doc_adresse: str | None,
    doc_cp: str | None,
    doc_ville: str | None,
) -> tuple[CrossCheckStatus, float, str | None]:
    """
    Compare deux adresses et retourne (status, confidence, detail).

    Stratégie :
    1. Code postal identique + ville identique + adresse similaire → PASS
    2. Code postal identique + ville similaire                    → WARNING
    3. Code postal différent                                       → FAIL
    """
    # Code postal
    cp_match = (cerfa_cp or "").strip() == (doc_cp or "").strip()
    if not cp_match:
        return (
            CrossCheckStatus.FAIL,
            0.0,
            f"Code postal différent : Cerfa={cerfa_cp!r} vs document={doc_cp!r}",
        )

    # Ville
    ville_cerfa = _normalize_city(cerfa_ville or "")
    ville_doc = _normalize_city(doc_ville or "")
    ville_match = ville_cerfa == ville_doc

    if not ville_match:
        return (
            CrossCheckStatus.WARNING,
            0.6,
            f"Code postal identique mais ville différente : Cerfa={cerfa_ville!r} vs document={doc_ville!r}",
        )

    # Ligne d'adresse (optionnel — données parfois absentes sur titre séjour)
    if cerfa_adresse and doc_adresse:
        addr_cerfa = _normalize_address_component(cerfa_adresse)
        addr_doc = _normalize_address_component(doc_adresse)
        if addr_cerfa == addr_doc:
            return CrossCheckStatus.PASS, 1.0, None
        else:
            # Même CP + même ville mais numéro/voie différent → WARNING
            return (
                CrossCheckStatus.WARNING,
                0.75,
                f"CP et ville identiques mais adresse différente : {cerfa_adresse!r} vs {doc_adresse!r}. "
                "Vérification visuelle recommandée.",
            )

    # CP + ville OK, adresse non vérifiable
    return CrossCheckStatus.PASS, 0.9, "Adresse complète non disponible — CP et ville identiques"


class AddressCerfaDomicileCheck(BaseCrossCheck):
    """
    C-04 — Vérifie que l'adresse déclarée sur le Cerfa correspond
    au justificatif de domicile fourni.

    Règle : CP + ville doivent être identiques.
    L'adresse ligne 1 est vérifiée si disponible.
    """

    @property
    def name(self) -> str:
        return "address_cerfa_domicile"

    def run(
        self,
        cerfa: ExtractedCerfa,
        domicile: ExtractedDomicile,
    ) -> list[CrossCheckResult]:
        status, confidence, detail = _compare_addresses(
            cerfa_adresse=cerfa.adresse,
            cerfa_cp=cerfa.code_postal,
            cerfa_ville=cerfa.ville,
            doc_adresse=domicile.adresse_ligne1,
            doc_cp=domicile.code_postal,
            doc_ville=domicile.ville,
        )

        return [CrossCheckResult(
            rule_name="address_cerfa_vs_domicile",
            status=status,
            source_a="CERFA",
            source_b="DOMICILE",
            field="adresse",
            value_a=f"{cerfa.adresse or ''} {cerfa.code_postal or ''} {cerfa.ville or ''}".strip(),
            value_b=f"{domicile.adresse_ligne1} {domicile.code_postal} {domicile.ville}",
            confidence=confidence,
            detail=detail,
        )]


class AddressCerfaTitreSejourCheck(BaseCrossCheck):
    """
    C-05 — Pour les ressortissants étrangers (titre de séjour),
    vérifie la cohérence de l'adresse Cerfa avec celle du titre séjour
    si elle est disponible, ou signale l'impossibilité de vérifier.

    Note : les titres de séjour ne mentionnent pas toujours une adresse.
    Dans ce cas, le justificatif de domicile (C-04) reste la référence.
    Le check C-05 lève un WARNING si le titre séjour n'a pas d'adresse
    pour que l'opérateur sache qu'il ne peut pas croiser via ce document.
    """

    @property
    def name(self) -> str:
        return "address_cerfa_titre_sejour"

    def run(
        self,
        cerfa: ExtractedCerfa,
        identite: ExtractedIdentite,
    ) -> list[CrossCheckResult]:
        # Titre séjour uniquement
        if identite.type_document not in ("TITRE_SEJOUR",):
            return []  # C-05 ne s'applique pas (CNI / passeport)

        # Le modèle ExtractedIdentite ne stocke pas l'adresse du titre séjour
        # (les titres de séjour modernes ne l'affichent plus) → WARNING informatif
        return [CrossCheckResult(
            rule_name="address_cerfa_vs_titre_sejour",
            status=CrossCheckStatus.WARNING,
            source_a="CERFA",
            source_b="TITRE_SEJOUR",
            field="adresse",
            value_a=f"{cerfa.code_postal or ''} {cerfa.ville or ''}".strip(),
            value_b="non disponible",
            confidence=0.5,
            detail=(
                "Ressortissant étranger — l'adresse du titre de séjour n'est pas vérifiable "
                "automatiquement (non imprimée sur le titre moderne). "
                "Vérifier la cohérence via le justificatif de domicile (C-04)."
            ),
        )]
