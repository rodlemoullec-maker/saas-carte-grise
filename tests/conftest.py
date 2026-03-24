"""
Configuration pytest et fixtures partagées.
"""
from __future__ import annotations
import pytest
from datetime import date


@pytest.fixture
def sample_vin_valid():
    return "VF1RFD00068123456"

@pytest.fixture
def sample_vin_invalid_char():
    return "VF1RFD0006O123456"  # O interdit

@pytest.fixture
def sample_siret_valid():
    return "73282932000074"  # SIRET de test INSEE

@pytest.fixture
def sample_siret_invalid():
    return "12345678901234"

@pytest.fixture
def reference_date():
    return date(2026, 3, 24)
