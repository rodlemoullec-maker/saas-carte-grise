"""
Tests end-to-end — API complète.

TODO: tester l'API FastAPI avec httpx AsyncClient.
TODO: tester le flux complet upload → pipeline → décision.
"""
from __future__ import annotations
import pytest


@pytest.mark.skip(reason="TODO: setup base de données de test")
async def test_create_dossier_and_get_decision():
    pass
