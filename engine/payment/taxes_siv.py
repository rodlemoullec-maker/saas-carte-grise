"""
Paiement des TAXES D'IMMATRICULATION — c'est l'argent de l'Etat.

SEPARATION CLAIRE avec les honoraires :
  - Les honoraires (payment/honoraires.py) = argent du porteur de projet → Stripe/PayPlug
  - Les taxes (ce fichier) = argent de l'Etat → paye dans le formulaire web SIV

PROBLEME NON RESOLU (au 2026-03-26) :
  Le porteur du projet est habilite SIV SANS agrement Tresor Public.
  Sans agrement, il ne peut PAS percevoir les taxes pour le compte de l'Etat.
  Les taxes se paient par CB dans le formulaire web SIV au moment de la soumission.

  Questions en attente de reponse ANTS (siv-pha@interieur.gouv.fr) :
  1. Le formulaire SIV habilite sans agrement propose-t-il un paiement CB ?
  2. Quelle CB est acceptee (pro, client, mandataire) ?
  3. Existe-t-il un mecanisme de bon d'operation (soumission + paiement separe) ?

IMPACT :
  - Full Service : BLOQUE tant que le mecanisme exact n'est pas confirme
  - SaaS : PAS BLOQUE (le pro paie ses taxes dans son propre SIV)
  - Estimation des taxes (engine/taxes/calculator.py) : FONCTIONNE (indicatif)

Ce module prepare l'architecture pour les 3 scenarios possibles une fois
la reponse ANTS recue.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


class TaxPaymentMethod(str, Enum):
    """Methodes de paiement des taxes — a confirmer apres reponse ANTS."""
    CB_DANS_SIV = "cb_dans_siv"           # CB du pro/client saisie dans le formulaire SIV
    BON_OPERATION = "bon_operation"         # Soumission SIV + paiement separe
    PRELEVEMENT_AGREMENT = "prelevement"   # Si agrement obtenu (peu probable)
    UNKNOWN = "unknown"                     # En attente de reponse ANTS


@dataclass
class TaxPaymentStatus:
    method: TaxPaymentMethod
    amount_cents: int
    paid: bool = False
    siv_transaction_id: str | None = None
    error: str | None = None
    notes: str | None = None


class TaxesSIVService:
    """
    Gere le paiement des taxes d'immatriculation.

    Ce service est un PLACEHOLDER en attente de la reponse ANTS.
    Il prepare les 3 architectures possibles.
    """

    def __init__(self):
        self.method = TaxPaymentMethod.UNKNOWN

    def get_tax_amount(self, tax_estimate: dict) -> int:
        """Retourne le montant total des taxes en centimes."""
        total = tax_estimate.get("total", 0)
        return int(total * 100)

    async def prepare_tax_payment(
        self,
        dossier_id: str,
        tax_estimate: dict,
        service_mode: str,
    ) -> TaxPaymentStatus:
        """
        Prepare le paiement des taxes selon le mode de service.

        SaaS : retourne les infos pour que le pro paie dans son SIV (rien a faire cote nous)
        Full Service : selon le mecanisme confirme par l'ANTS
        """
        amount_cents = self.get_tax_amount(tax_estimate)

        if service_mode == "SAAS":
            # SaaS : le pro gere les taxes dans son propre SIV
            return TaxPaymentStatus(
                method=TaxPaymentMethod.CB_DANS_SIV,
                amount_cents=amount_cents,
                paid=False,
                notes=(
                    "Mode SaaS — le professionnel paie les taxes directement "
                    "dans son propre acces SIV. Montant estime : "
                    f"{amount_cents/100:.2f} EUR (indicatif, montant final = SIV)."
                ),
            )

        # Full Service : mecanisme en attente de confirmation ANTS
        if self.method == TaxPaymentMethod.UNKNOWN:
            return TaxPaymentStatus(
                method=TaxPaymentMethod.UNKNOWN,
                amount_cents=amount_cents,
                paid=False,
                error=(
                    "Mecanisme de paiement des taxes non confirme. "
                    "En attente de reponse ANTS (siv-pha@interieur.gouv.fr). "
                    "La soumission SIV Full Service est bloquee sur ce point."
                ),
            )

        # Scenario 1 : CB dans le formulaire SIV
        if self.method == TaxPaymentMethod.CB_DANS_SIV:
            return TaxPaymentStatus(
                method=TaxPaymentMethod.CB_DANS_SIV,
                amount_cents=amount_cents,
                paid=False,
                notes=(
                    f"L'operateur devra saisir la CB du pro dans le formulaire SIV. "
                    f"Montant estime : {amount_cents/100:.2f} EUR."
                ),
            )

        # Scenario 2 : Bon d'operation
        if self.method == TaxPaymentMethod.BON_OPERATION:
            return TaxPaymentStatus(
                method=TaxPaymentMethod.BON_OPERATION,
                amount_cents=amount_cents,
                paid=False,
                notes=(
                    "Soumission SIV sans paiement immediat. "
                    "Un bon d'operation sera genere pour paiement ulterieur."
                ),
            )

        return TaxPaymentStatus(
            method=self.method,
            amount_cents=amount_cents,
            paid=False,
        )
