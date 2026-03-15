"""Tests de la recherche véhicule multi-sources."""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.vehicle.search import search
from src.vehicle.types_mines import search_by_marque_modele, search_by_cnit


def test_search_by_marque():
    results = search_by_marque_modele("RENAULT")
    assert len(results) > 0
    assert results[0]["marque"].upper().startswith("RENAULT")


def test_search_by_marque_modele():
    results = search_by_marque_modele("BMW", "X3")
    assert len(results) > 0


def test_search_by_marque_inexistante():
    results = search_by_marque_modele("MARQUEINEXISTANTE999")
    assert len(results) == 0


def test_multi_source_vin_marque():
    result = search(vin="WBA11AG01MCF12345", marque="BMW", modele="X3")
    assert "vin_decoder" in result["sources"]
    assert "types_mines" in result["sources"]
    assert result["constructeur_vin"] == "BMW"
    assert result.get("puissance_fiscale") is not None


def test_multi_source_sans_stock():
    result = search(vin="WBA11AG01MCF12345", marque="BMW")
    assert "stock_interne" not in result["sources"]


def test_multi_source_avec_stock():
    result = search(vin="WBA11AG01MCF12345", marque="BMW", use_stock=True)
    # Stock cherché mais véhicule pas trouvé (normal)
    assert "stock_interne" not in result["sources"]


def test_completude():
    result = search(vin="WBA11AG01MCF12345", marque="BMW", modele="X3")
    assert result["completude"] == "4/4"


def test_vin_seul():
    result = search(vin="JYARN491000012345")
    assert "vin_decoder" in result["sources"]
    assert result["constructeur_vin"] == "Yamaha"


if __name__ == "__main__":
    for name, func in sorted(globals().items()):
        if name.startswith("test_") and callable(func):
            try:
                func()
                print(f"  ✓ {name}")
            except AssertionError as e:
                print(f"  ✗ {name}: {e}")
    print("Tests vehicle search terminés.")
