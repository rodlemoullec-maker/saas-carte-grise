"""Tests du calcul des taxes carte grise."""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.taxes.calculator import calculer_taxes, get_regions


def test_regions_disponibles():
    regions = get_regions()
    assert len(regions) > 10
    assert "ile_de_france" in regions
    assert "auvergne_rhone_alpes" in regions


def test_voiture_occasion_idf():
    t = calculer_taxes(puissance_fiscale=7, region="ile_de_france", energie="ES",
                       co2=150, genre="VP", est_neuf=False)
    assert t["Y1_taxe_regionale"] == round(7 * 54.95, 2)
    assert t["Y4_malus_co2"] == 0.0  # Occasion = pas de malus
    assert t["Y5_malus_masse"] == 0.0
    assert t["Y6_taxe_fixe"] == 11.0
    assert t["total"] > 0


def test_moto_exempte_malus():
    t = calculer_taxes(puissance_fiscale=4, region="auvergne_rhone_alpes", energie="ES",
                       co2=100, genre="MTL", est_neuf=True)
    assert t["Y4_malus_co2"] == 0.0  # Moto exemptée
    assert t["Y5_malus_masse"] == 0.0


def test_electrique_exoneree():
    t = calculer_taxes(puissance_fiscale=6, region="ile_de_france", energie="EL",
                       co2=0, genre="VP", est_neuf=True)
    assert t["Y1_taxe_regionale"] == 0.0  # Exonéré


def test_hybride_demi_tarif():
    t = calculer_taxes(puissance_fiscale=10, region="ile_de_france", energie="EH",
                       co2=50, genre="VP", est_neuf=False)
    assert t["Y1_taxe_regionale"] == 10 * 54.95 * 0.5


def test_malus_co2_neuf():
    t = calculer_taxes(puissance_fiscale=15, region="ile_de_france", energie="ES",
                       co2=200, genre="VP", est_neuf=True)
    assert t["Y4_malus_co2"] > 0  # 200 g/km > seuil


def test_malus_masse_neuf():
    t = calculer_taxes(puissance_fiscale=15, region="ile_de_france", energie="ES",
                       co2=100, masse=2000, genre="VP", est_neuf=True)
    assert t["Y5_malus_masse"] == (2000 - 1800) * 10  # 200 kg × 10€


def test_sous_seuil_co2():
    t = calculer_taxes(puissance_fiscale=5, region="ile_de_france", energie="ES",
                       co2=100, genre="VP", est_neuf=True)
    assert t["Y4_malus_co2"] == 0.0  # 100 < 118 seuil


def test_remorque_exempte():
    t = calculer_taxes(puissance_fiscale=0, region="ile_de_france", energie="",
                       co2=0, genre="REM", est_neuf=True)
    assert t["Y4_malus_co2"] == 0.0
    assert t["Y5_malus_masse"] == 0.0


def test_taxe_formation_pro():
    t = calculer_taxes(puissance_fiscale=7, region="ile_de_france", energie="ES",
                       genre="VP", est_professionnel=True)
    y1 = 7 * 54.95
    assert t["Y3_taxe_formation"] == round(y1 * 0.01, 2)


def test_particulier_pas_y3():
    t = calculer_taxes(puissance_fiscale=7, region="ile_de_france", energie="ES",
                       genre="VP", est_professionnel=False)
    assert t["Y3_taxe_formation"] == 0.0


def test_region_inconnue():
    t = calculer_taxes(puissance_fiscale=7, region="mars", energie="ES", genre="VP")
    assert t["Y1_taxe_regionale"] == 0.0
    assert "Y1_warning" in t["details"]


if __name__ == "__main__":
    for name, func in sorted(globals().items()):
        if name.startswith("test_") and callable(func):
            try:
                func()
                print(f"  ✓ {name}")
            except AssertionError as e:
                print(f"  ✗ {name}: {e}")
    print("Tests taxes terminés.")
