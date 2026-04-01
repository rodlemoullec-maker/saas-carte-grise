"""
Cross-checks spécifiques aux dossiers VO (véhicule d'occasion).

Règles implémentées :
  C-11 — Chaîne de propriété : vendeur DA = titulaire CG barrée
  C-12 — Cohérence des dates : CG barrée ≤ DA ≤ cession, DA enregistrée < 15j
  C-13 — Signatures ↔ co-titulaires : signatures CG + cession ≥ nb co-titulaires
"""
from __future__ import annotations

from engine.cross_checks.base import BaseCrossCheck
from engine.models.decision import CrossCheckResult, CrossCheckStatus
from engine.models.documents import (
    ExtractedCGBarree,
    ExtractedCession,
    ExtractedDA,
    ExtractedRecepisseDA,
)
from engine.normalizers.names import normalize_name, match_names


class ChaineProprieteCheck(BaseCrossCheck):
    """
    C-11 — Le vendeur dans la DA doit être le titulaire de la CG barrée.
    Si la CG est co-titulaire, les deux noms doivent être vérifiés.
    """

    @property
    def name(self) -> str:
        return "chaine_propriete"

    def run(
        self,
        cg: ExtractedCGBarree,
        da: ExtractedDA,
        cession: ExtractedCession | None = None,
    ) -> list[CrossCheckResult]:
        results = []

        # CG titulaire vs DA vendeur_nom
        if cg.titulaire_nom and da.vendeur_nom:
            match_result = match_names(cg.titulaire_nom, da.vendeur_nom)
            score = match_result.confidence
            if score >= 0.97:
                status = CrossCheckStatus.PASS
                detail = None
            elif score >= 0.85:
                status = CrossCheckStatus.WARNING
                detail = f"Nom vendeur DA proche mais différent du titulaire CG (score {score:.0%})"
            else:
                status = CrossCheckStatus.FAIL
                detail = (
                    f"Vendeur DA ({da.vendeur_nom!r}) ≠ titulaire CG ({cg.titulaire_nom!r}) "
                    f"— score {score:.0%}"
                )
            results.append(CrossCheckResult(
                rule_name="vendeur_da_vs_titulaire_cg",
                status=status,
                source_a="CG_BARREE",
                source_b="DA",
                field="nom_titulaire",
                value_a=cg.titulaire_nom,
                value_b=da.vendeur_nom,
                confidence=score,
                detail=detail,
            ))
        else:
            results.append(CrossCheckResult(
                rule_name="vendeur_da_vs_titulaire_cg",
                status=CrossCheckStatus.WARNING,
                source_a="CG_BARREE",
                source_b="DA",
                field="nom_titulaire",
                value_a=cg.titulaire_nom or "",
                value_b=da.vendeur_nom or "",
                confidence=0.5,
                detail="Nom titulaire CG ou vendeur DA absent — vérification manuelle requise",
            ))

        # VIN cohérence CG ↔ DA
        if cg.vin and da.vin:
            if cg.vin.upper() == da.vin.upper():
                results.append(CrossCheckResult(
                    rule_name="vin_cg_vs_da",
                    status=CrossCheckStatus.PASS,
                    source_a="CG_BARREE", source_b="DA",
                    field="vin",
                    value_a=cg.vin, value_b=da.vin,
                    confidence=1.0,
                ))
            else:
                results.append(CrossCheckResult(
                    rule_name="vin_cg_vs_da",
                    status=CrossCheckStatus.FAIL,
                    source_a="CG_BARREE", source_b="DA",
                    field="vin",
                    value_a=cg.vin, value_b=da.vin,
                    confidence=0.0,
                    detail=f"VIN CG barrée ({cg.vin}) ≠ VIN DA ({da.vin})",
                ))

        # SIRET pro : vendeur Cerfa cession = pro (si cession fournie)
        if cession and cession.vendeur_siret and da.siret_pro:
            if cession.vendeur_siret == da.siret_pro:
                results.append(CrossCheckResult(
                    rule_name="siret_cession_vs_da",
                    status=CrossCheckStatus.PASS,
                    source_a="CERFA_CESSION", source_b="DA",
                    field="siret_vendeur",
                    value_a=cession.vendeur_siret, value_b=da.siret_pro,
                    confidence=1.0,
                ))
            else:
                results.append(CrossCheckResult(
                    rule_name="siret_cession_vs_da",
                    status=CrossCheckStatus.FAIL,
                    source_a="CERFA_CESSION", source_b="DA",
                    field="siret_vendeur",
                    value_a=cession.vendeur_siret, value_b=da.siret_pro,
                    confidence=0.0,
                    detail=(
                        f"SIRET vendeur cession ({cession.vendeur_siret}) "
                        f"≠ SIRET pro DA ({da.siret_pro})"
                    ),
                ))

        return results


class DatesCGBarreeCheck(BaseCrossCheck):
    """
    C-12 — Cohérence temporelle des dates VO.

    Règles :
    - date_vente (CG barrée) ≤ date_achat (DA)
    - date_achat (DA) ≤ date_cession (cession)
    - date_enregistrement (récépissé DA) ≤ date_achat + 15 jours
    """

    @property
    def name(self) -> str:
        return "dates_cg_barree"

    def run(
        self,
        cg: ExtractedCGBarree,
        da: ExtractedDA,
        cession: ExtractedCession | None = None,
        recepisse: ExtractedRecepisseDA | None = None,
    ) -> list[CrossCheckResult]:
        results = []

        # CG date_vente ≤ DA date_achat
        if cg.date_vente and da.date_achat:
            if cg.date_vente <= da.date_achat:
                results.append(CrossCheckResult(
                    rule_name="cg_date_vs_da_date",
                    status=CrossCheckStatus.PASS,
                    source_a="CG_BARREE", source_b="DA",
                    field="date_vente",
                    value_a=str(cg.date_vente), value_b=str(da.date_achat),
                    confidence=1.0,
                ))
            else:
                delta = (cg.date_vente - da.date_achat).days
                results.append(CrossCheckResult(
                    rule_name="cg_date_vs_da_date",
                    status=CrossCheckStatus.FAIL,
                    source_a="CG_BARREE", source_b="DA",
                    field="date_vente",
                    value_a=str(cg.date_vente), value_b=str(da.date_achat),
                    confidence=0.0,
                    detail=(
                        f"Date vente CG ({cg.date_vente}) postérieure à date achat DA "
                        f"({da.date_achat}) de {delta} jour(s)"
                    ),
                ))

        # DA date_achat ≤ cession date_cession
        if da.date_achat and cession and cession.date_cession:
            if da.date_achat <= cession.date_cession:
                results.append(CrossCheckResult(
                    rule_name="da_date_vs_cession_date",
                    status=CrossCheckStatus.PASS,
                    source_a="DA", source_b="CERFA_CESSION",
                    field="date_achat",
                    value_a=str(da.date_achat), value_b=str(cession.date_cession),
                    confidence=1.0,
                ))
            else:
                delta = (da.date_achat - cession.date_cession).days
                results.append(CrossCheckResult(
                    rule_name="da_date_vs_cession_date",
                    status=CrossCheckStatus.FAIL,
                    source_a="DA", source_b="CERFA_CESSION",
                    field="date_achat",
                    value_a=str(da.date_achat), value_b=str(cession.date_cession),
                    confidence=0.0,
                    detail=(
                        f"Date achat DA ({da.date_achat}) postérieure à date cession "
                        f"({cession.date_cession}) de {delta} jour(s)"
                    ),
                ))

        # Récépissé DA : enregistré dans les 15 jours après l'achat
        if recepisse and recepisse.date_enregistrement and da.date_achat:
            delta_recepisse = (recepisse.date_enregistrement - da.date_achat).days
            if delta_recepisse <= 15:
                results.append(CrossCheckResult(
                    rule_name="recepisse_da_delay",
                    status=CrossCheckStatus.PASS,
                    source_a="DA", source_b="RECEPISEE_DA",
                    field="date_enregistrement",
                    value_a=str(da.date_achat), value_b=str(recepisse.date_enregistrement),
                    confidence=1.0,
                ))
            else:
                results.append(CrossCheckResult(
                    rule_name="recepisse_da_delay",
                    status=CrossCheckStatus.FAIL,
                    source_a="DA", source_b="RECEPISEE_DA",
                    field="date_enregistrement",
                    value_a=str(da.date_achat), value_b=str(recepisse.date_enregistrement),
                    confidence=0.0,
                    detail=(
                        f"Récépissé DA enregistré {delta_recepisse} jours après l'achat "
                        f"(max 15 jours réglementaires)"
                    ),
                ))

        return results


class SignaturesCotitulaireCheck(BaseCrossCheck):
    """
    C-13 — Vérification des signatures selon le type de transaction.

    Règles de signature (pro = toujours le vendeur) :
    - VN : aucune signature client requise (pro soumet comme vendeur professionnel)
    - VO — CG barrée : signatures_count ≥ max(1, co_titulaires_count) côté pro
    - VO — Cession : signatures_vendeur = True (pro, côté vendeur)
    - VO — Cession : signature_acheteur = True (client, seule signature requise)
    - VO — Cession : tampon_siret = True (cachet pro, apposé automatiquement)

    Le mandat 13757 n'est PAS nécessaire quand le pro est le vendeur.
    """

    @property
    def name(self) -> str:
        return "signatures_cotitulaire"

    def run(
        self,
        cg: ExtractedCGBarree,
        cession: ExtractedCession | None = None,
    ) -> list[CrossCheckResult]:
        results = []
        nb_required = max(1, cg.co_titulaires_count)

        # VO — CG barrée : signature(s) du pro (ancien titulaire)
        if cg.signatures_count >= nb_required:
            results.append(CrossCheckResult(
                rule_name="cg_signatures_vs_cotitulaires",
                status=CrossCheckStatus.PASS,
                source_a="CG_BARREE", source_b="CG_BARREE",
                field="signatures_count",
                value_a=str(cg.signatures_count), value_b=str(nb_required),
                confidence=1.0,
            ))
        else:
            results.append(CrossCheckResult(
                rule_name="cg_signatures_vs_cotitulaires",
                status=CrossCheckStatus.FAIL,
                source_a="CG_BARREE", source_b="CG_BARREE",
                field="signatures_count",
                value_a=str(cg.signatures_count), value_b=str(nb_required),
                confidence=0.0,
                detail=(
                    f"{cg.signatures_count} signature(s) détectée(s) sur la CG barrée, "
                    f"{nb_required} requise(s) ({cg.co_titulaires_count} co-titulaire(s))"
                ),
            ))

        if cession:
            # VO — Cession : signature vendeur (pro) — BLOQUANT
            if cession.signatures_vendeur:
                results.append(CrossCheckResult(
                    rule_name="cession_signature_vendeur",
                    status=CrossCheckStatus.PASS,
                    source_a="CERFA_CESSION", source_b="CERFA_CESSION",
                    field="signatures_vendeur",
                    value_a="True", value_b="True",
                    confidence=1.0,
                ))
            else:
                results.append(CrossCheckResult(
                    rule_name="cession_signature_vendeur",
                    status=CrossCheckStatus.FAIL,
                    source_a="CERFA_CESSION", source_b="CERFA_CESSION",
                    field="signatures_vendeur",
                    value_a="False", value_b="True",
                    confidence=0.0,
                    detail="Cerfa cession non signé par le vendeur (pro)",
                ))

            # VO — Cession : signature acquéreur (client) — BLOQUANT
            # C'est la SEULE signature requise du client dans tout le parcours
            if cession.signature_acheteur:
                results.append(CrossCheckResult(
                    rule_name="cession_signature_acheteur",
                    status=CrossCheckStatus.PASS,
                    source_a="CERFA_CESSION", source_b="CERFA_CESSION",
                    field="signature_acheteur",
                    value_a="True", value_b="True",
                    confidence=1.0,
                ))
            else:
                results.append(CrossCheckResult(
                    rule_name="cession_signature_acheteur",
                    status=CrossCheckStatus.FAIL,
                    source_a="CERFA_CESSION", source_b="CERFA_CESSION",
                    field="signature_acheteur",
                    value_a="False", value_b="True",
                    confidence=0.0,
                    detail="Cerfa cession non signé par l'acquéreur (client)",
                ))

            # VO — Cession : tampon SIRET (cachet pro, appos�� automatiquement)
            if cession.tampon_siret:
                results.append(CrossCheckResult(
                    rule_name="cession_tampon_siret",
                    status=CrossCheckStatus.PASS,
                    source_a="CERFA_CESSION", source_b="CERFA_CESSION",
                    field="tampon_siret",
                    value_a="True", value_b="True",
                    confidence=1.0,
                ))
            else:
                results.append(CrossCheckResult(
                    rule_name="cession_tampon_siret",
                    status=CrossCheckStatus.WARNING,
                    source_a="CERFA_CESSION", source_b="CERFA_CESSION",
                    field="tampon_siret",
                    value_a="False", value_b="True",
                    confidence=0.7,
                    detail="Tampon SIRET pro absent sur le Cerfa cession (sera apposé automatiquement)",
                ))

        return results


