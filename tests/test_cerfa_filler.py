"""Tests du pré-remplissage CERFA."""

import sys
import os
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.cerfa.filler import fill_cerfa_from_dossier, get_field_positions
from config.settings import CERFA_13750_TEMPLATE, OUTPUT_DIR


def test_field_positions_exist():
    positions = get_field_positions()
    assert len(positions) > 20
    assert "immatriculation" in positions
    assert "vin" in positions
    assert "marque" in positions
    assert "Y1" in positions
    assert "total_taxes" in positions


def test_template_exists():
    assert CERFA_13750_TEMPLATE.exists(), f"Template manquant: {CERFA_13750_TEMPLATE}"


def test_generate_cerfa():
    demandeur = {
        "nom": "TEST",
        "prenom": "Unitaire",
        "date_naissance": "01/01/1990",
        "adresse_code_postal": "75001",
        "adresse_ville": "PARIS",
    }
    vehicule = {
        "immatriculation": "ZZ-999-ZZ",
        "marque": "TEST",
        "vin": "ZZZZZZZZZZZZZZZZZ",
        "genre": "VP",
        "energie": "ES",
        "puissance_fiscale": 5,
    }
    taxes = {
        "Y1_taxe_regionale": 100.0,
        "Y3_taxe_formation": 1.0,
        "Y4_malus_co2": 0.0,
        "Y5_malus_masse": 0.0,
        "Y6_taxe_fixe": 11.0,
        "total": 112.0,
    }

    path = fill_cerfa_from_dossier(demandeur, vehicule, taxes, "test_unitaire.pdf")
    assert os.path.exists(path)
    assert os.path.getsize(path) > 50000  # PDF doit faire plus de 50KB

    # Nettoyage
    os.remove(path)


def test_generate_cerfa_moto():
    demandeur = {"nom": "MOTO", "prenom": "Test"}
    vehicule = {
        "immatriculation": "AA-111-AA",
        "marque": "YAMAHA",
        "vin": "JYARN491000099999",
        "genre": "MTL",
        "energie": "ES",
        "puissance_fiscale": 4,
        "nb_places": 2,
    }
    taxes = {"Y1_taxe_regionale": 172.0, "Y6_taxe_fixe": 11.0, "total": 183.0}

    path = fill_cerfa_from_dossier(demandeur, vehicule, taxes, "test_moto.pdf")
    assert os.path.exists(path)
    os.remove(path)


if __name__ == "__main__":
    for name, func in sorted(globals().items()):
        if name.startswith("test_") and callable(func):
            try:
                func()
                print(f"  ✓ {name}")
            except AssertionError as e:
                print(f"  ✗ {name}: {e}")
    print("Tests CERFA filler terminés.")
