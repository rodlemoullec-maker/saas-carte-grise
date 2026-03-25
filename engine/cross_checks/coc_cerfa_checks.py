"""
Cross-checks COC ↔ Cerfa et cohérence données techniques véhicule.

Règles implémentées :
  C-08 — CNIT ↔ base UTAC (validation format + stub appel API)
  C-09 — Puissance fiscale COC vs Cerfa (±1CV → WARNING, ±3CV → BLOCKING)
  C-10 — CO2 : s'assurer que la valeur WLTP est utilisée pour le malus
          (et non NEDC) — applicable si les deux sont présentes sur le COC
"""
from __future__ import annotations

import re

from engine.cross_checks.base import BaseCrossCheck
from engine.models.decision import CrossCheckResult, CrossCheckStatus
from engine.models.documents import ExtractedCOC, ExtractedCerfa


# Format CNIT : 2 lettres + 6 chiffres + 1 lettre (ex. AA000001A)
# Format exact peut varier selon constructeur — on vérifie le pattern minimal
_CNIT_PATTERN = re.compile(r"^[A-Z]{1,3}\d{5,7}[A-Z0-9]{1,3}$", re.IGNORECASE)


class CNITUTACCheck(BaseCrossCheck):
    """
    C-08 — Vérifie la cohérence du CNIT avec la base homologation UTAC.

    Phase 1 : validation du format CNIT (synchrone, sans appel réseau).
    Phase 2 (TODO) : appel API UTAC/OTC pour vérifier que le CNIT existe
                     et que les caractéristiques correspondent au COC.

    En l'absence d'API UTAC publique directe, ce check lève un WARNING
    si le CNIT est absent ou mal formé, et un INFO si présent mais non
    encore vérifié en base.
    """

    @property
    def name(self) -> str:
        return "cnit_utac"

    def run(self, coc: ExtractedCOC) -> list[CrossCheckResult]:
        results = []

        if not coc.cnit:
            results.append(CrossCheckResult(
                rule_name="cnit_format",
                status=CrossCheckStatus.WARNING,
                source_a="COC", source_b="UTAC",
                field="cnit",
                value_a="", value_b="",
                confidence=0.5,
                detail=(
                    "CNIT absent sur le COC — impossible de vérifier l'homologation UTAC. "
                    "Contacter le constructeur si nécessaire pour la saisie SIV."
                ),
            ))
            return results

        cnit = coc.cnit.strip().upper()

        if not _CNIT_PATTERN.match(cnit):
            results.append(CrossCheckResult(
                rule_name="cnit_format",
                status=CrossCheckStatus.WARNING,
                source_a="COC", source_b="UTAC",
                field="cnit",
                value_a=cnit, value_b="",
                confidence=0.4,
                detail=f"Format CNIT suspect : {cnit!r} — vérifier le COC original",
            ))
        else:
            # Format OK — vérification UTAC en base non encore implémentée
            results.append(CrossCheckResult(
                rule_name="cnit_format",
                status=CrossCheckStatus.PASS,
                source_a="COC", source_b="UTAC",
                field="cnit",
                value_a=cnit, value_b="",
                confidence=0.8,
                detail="Format CNIT valide — vérification base UTAC (TODO: appel API OTC)",
            ))

        # TODO: appel async integrations/utac.py pour validation en base UTAC
        # utac_result = await UTACClient().check_cnit(cnit, coc.marque, coc.energie)

        return results


class PuissanceFiscaleCheck(BaseCrossCheck):
    """
    C-09 — Vérifie la cohérence de la puissance fiscale (CV) entre le COC
    (case P.6 — puissance administrative) et le Cerfa demande de CG.

    Tolérances réglementaires :
    - Écart ≤ 1 CV  → WARNING (possible arrondi OCR)
    - Écart 2 CV    → WARNING fort (vérification manuelle obligatoire)
    - Écart ≥ 3 CV  → BLOCKING (incohérence documentaire)

    Note : la puissance fiscale FR est calculée selon la formule DIN/SIV et
    peut différer de ±1 CV selon les arrondis appliqués par le constructeur
    vs l'administration.
    """

    @property
    def name(self) -> str:
        return "puissance_fiscale"

    def run(self, coc: ExtractedCOC, cerfa: ExtractedCerfa) -> list[CrossCheckResult]:
        if coc.puissance_fiscale_cv is None or cerfa.puissance_fiscale_cv is None:
            # Données manquantes — on ne peut pas comparer
            if coc.puissance_fiscale_cv is None and cerfa.puissance_fiscale_cv is None:
                return []  # Rien à croiser
            missing = "COC" if coc.puissance_fiscale_cv is None else "Cerfa"
            return [CrossCheckResult(
                rule_name="puissance_fiscale_coc_cerfa",
                status=CrossCheckStatus.WARNING,
                source_a="COC", source_b="CERFA",
                field="puissance_fiscale_cv",
                value_a=str(coc.puissance_fiscale_cv or ""),
                value_b=str(cerfa.puissance_fiscale_cv or ""),
                confidence=0.5,
                detail=f"Puissance fiscale absente sur {missing} — vérification impossible",
            )]

        delta = abs(coc.puissance_fiscale_cv - cerfa.puissance_fiscale_cv)

        if delta == 0:
            return [CrossCheckResult(
                rule_name="puissance_fiscale_coc_cerfa",
                status=CrossCheckStatus.PASS,
                source_a="COC", source_b="CERFA",
                field="puissance_fiscale_cv",
                value_a=str(coc.puissance_fiscale_cv),
                value_b=str(cerfa.puissance_fiscale_cv),
                confidence=1.0,
            )]

        if delta == 1:
            return [CrossCheckResult(
                rule_name="puissance_fiscale_coc_cerfa",
                status=CrossCheckStatus.WARNING,
                source_a="COC", source_b="CERFA",
                field="puissance_fiscale_cv",
                value_a=str(coc.puissance_fiscale_cv),
                value_b=str(cerfa.puissance_fiscale_cv),
                confidence=0.8,
                detail=(
                    f"Écart de {delta} CV entre COC ({coc.puissance_fiscale_cv} CV) "
                    f"et Cerfa ({cerfa.puissance_fiscale_cv} CV) — "
                    "possible arrondi OCR ou différence de calcul. Vérification visuelle recommandée."
                ),
            )]

        if delta == 2:
            return [CrossCheckResult(
                rule_name="puissance_fiscale_coc_cerfa",
                status=CrossCheckStatus.WARNING,
                source_a="COC", source_b="CERFA",
                field="puissance_fiscale_cv",
                value_a=str(coc.puissance_fiscale_cv),
                value_b=str(cerfa.puissance_fiscale_cv),
                confidence=0.5,
                detail=(
                    f"Écart de {delta} CV entre COC ({coc.puissance_fiscale_cv} CV) "
                    f"et Cerfa ({cerfa.puissance_fiscale_cv} CV) — "
                    "vérification manuelle OBLIGATOIRE avant soumission SIV."
                ),
            )]

        # delta >= 3 → BLOCKING
        return [CrossCheckResult(
            rule_name="puissance_fiscale_coc_cerfa",
            status=CrossCheckStatus.FAIL,
            source_a="COC", source_b="CERFA",
            field="puissance_fiscale_cv",
            value_a=str(coc.puissance_fiscale_cv),
            value_b=str(cerfa.puissance_fiscale_cv),
            confidence=0.0,
            detail=(
                f"Incohérence critique : COC indique {coc.puissance_fiscale_cv} CV, "
                f"Cerfa indique {cerfa.puissance_fiscale_cv} CV (écart {delta} CV ≥ 3 CV). "
                "Dossier bloqué — vérifier les documents originaux."
            ),
        )]


class CO2WLTPCheck(BaseCrossCheck):
    """
    C-10 — Vérifie que la valeur CO2 utilisée pour le calcul du malus
    écologique est bien le cycle WLTP (et non NEDC).

    Règle (art. 1011 bis CGI, applicable depuis le 01/01/2021) :
    - Véhicules immatriculés après 01/01/2021 : WLTP OBLIGATOIRE pour le malus
    - Véhicules antérieurs : NEDC accepté
    - Si les deux sont présents : utiliser WLTP (jamais NEDC)

    Ce check détecte les situations à risque et informe le pipeline de
    tarification pour qu'il utilise la bonne valeur.
    """

    @property
    def name(self) -> str:
        return "co2_wltp_check"

    def run(self, coc: ExtractedCOC) -> list[CrossCheckResult]:
        results = []

        has_wltp = coc.co2_wltp is not None and coc.co2_wltp > 0
        has_nedc = coc.co2_nedc is not None and coc.co2_nedc > 0

        if not has_wltp and not has_nedc:
            # Électrique pur (CO2=0) ou données absentes
            if coc.energie and "electrique" in coc.energie.lower():
                results.append(CrossCheckResult(
                    rule_name="co2_wltp_source",
                    status=CrossCheckStatus.PASS,
                    source_a="COC", source_b="SYSTEM",
                    field="co2_wltp",
                    value_a="0", value_b="",
                    confidence=1.0,
                    detail="Véhicule électrique — CO2=0, pas de malus applicable",
                ))
            else:
                results.append(CrossCheckResult(
                    rule_name="co2_wltp_source",
                    status=CrossCheckStatus.WARNING,
                    source_a="COC", source_b="SYSTEM",
                    field="co2_wltp",
                    value_a="", value_b="",
                    confidence=0.4,
                    detail=(
                        "Valeur CO2 absente sur le COC — impossible de calculer le malus. "
                        "Vérifier le COC (case V.7) ou consulter la base UTAC."
                    ),
                ))
            return results

        if has_wltp and has_nedc:
            # Les deux présents — s'assurer que WLTP sera utilisé
            results.append(CrossCheckResult(
                rule_name="co2_wltp_source",
                status=CrossCheckStatus.PASS,
                source_a="COC", source_b="SYSTEM",
                field="co2_wltp",
                value_a=str(coc.co2_wltp),
                value_b=str(coc.co2_nedc),
                confidence=1.0,
                detail=(
                    f"WLTP={coc.co2_wltp} g/km | NEDC={coc.co2_nedc} g/km — "
                    "calcul malus basé sur WLTP (réglementation 2021+)"
                ),
            ))
            # Alerte si l'écart WLTP/NEDC est > 20% (peut impacter fortement le malus)
            if coc.co2_nedc and coc.co2_wltp and coc.co2_nedc > 0:
                ratio = coc.co2_wltp / coc.co2_nedc
                if ratio > 1.20:
                    results.append(CrossCheckResult(
                        rule_name="co2_wltp_nedc_gap",
                        status=CrossCheckStatus.WARNING,
                        source_a="COC", source_b="SYSTEM",
                        field="co2_wltp",
                        value_a=str(coc.co2_wltp),
                        value_b=str(coc.co2_nedc),
                        confidence=0.8,
                        detail=(
                            f"Écart WLTP/NEDC > 20% ({coc.co2_wltp} vs {coc.co2_nedc} g/km) — "
                            "l'estimation NEDC présentée au client peut sous-évaluer le malus réel."
                        ),
                    ))

        elif has_nedc and not has_wltp:
            # Seulement NEDC — vérifier si le véhicule est post-2021
            if coc.date_premiere_immat_ue and coc.date_premiere_immat_ue.year >= 2021:
                results.append(CrossCheckResult(
                    rule_name="co2_wltp_source",
                    status=CrossCheckStatus.FAIL,
                    source_a="COC", source_b="SYSTEM",
                    field="co2_wltp",
                    value_a="", value_b=str(coc.co2_nedc),
                    confidence=0.0,
                    detail=(
                        f"Véhicule 1ère immat ≥ 2021 mais seul le CO2 NEDC ({coc.co2_nedc} g/km) "
                        "est disponible. Le SIV exige le WLTP depuis le 01/01/2021. "
                        "Demander le COC complet au constructeur."
                    ),
                ))
            else:
                results.append(CrossCheckResult(
                    rule_name="co2_wltp_source",
                    status=CrossCheckStatus.WARNING,
                    source_a="COC", source_b="SYSTEM",
                    field="co2_wltp",
                    value_a="", value_b=str(coc.co2_nedc),
                    confidence=0.7,
                    detail=(
                        f"Seul le CO2 NEDC ({coc.co2_nedc} g/km) disponible. "
                        "Acceptable pour véhicule pré-2021 — vérifier la date de 1ère immat."
                    ),
                ))

        elif has_wltp and not has_nedc:
            results.append(CrossCheckResult(
                rule_name="co2_wltp_source",
                status=CrossCheckStatus.PASS,
                source_a="COC", source_b="SYSTEM",
                field="co2_wltp",
                value_a=str(coc.co2_wltp), value_b="",
                confidence=1.0,
                detail=f"CO2 WLTP={coc.co2_wltp} g/km — source correcte pour calcul malus",
            ))

        return results
