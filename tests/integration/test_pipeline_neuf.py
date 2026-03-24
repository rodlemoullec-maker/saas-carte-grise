"""
Tests d'intégration — Pipeline complet véhicule neuf.

TODO: tester avec des documents synthétiques (fixtures anonymisées).
TODO: vérifier que le pipeline complet produit la décision attendue.
"""
from __future__ import annotations
import pytest


class TestPipelineNeuf:

    @pytest.mark.skip(reason="TODO: créer fixtures documents de test")
    def test_dossier_complet_accepte(self):
        """Un dossier complet et cohérent doit être ACCEPTE."""
        pass

    @pytest.mark.skip(reason="TODO: créer fixtures documents de test")
    def test_vin_mismatch_rejet(self):
        """Un VIN différent entre COC et facture doit être REJET."""
        pass
