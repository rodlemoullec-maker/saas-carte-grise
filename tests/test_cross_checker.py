"""Tests de la cross-validation inter-documents."""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.validation.cross_checker import validate_dossier, _fuzzy_match, _parse_date


def _dossier_complet():
    """Retourne un dossier complet et cohérent."""
    return {
        "carte_grise": {
            "A_immatriculation": "AB-123-CD",
            "E_vin": "JYARN491000012345",
        },
        "certificat_cession": {
            "immatriculation": "AB-123-CD",
            "vin": "JYARN491000012345",
            "acheteur_nom": "DUPONT",
            "acheteur_prenom": "Jean",
        },
        "cni": {
            "nom": "DUPONT",
            "prenom": "Jean",
            "date_validite": "15/06/2030",
        },
        "justificatif_domicile": {
            "date_document": "10/01/2026",
        },
    }


def test_dossier_complet_moto():
    docs = _dossier_complet()
    r = validate_dossier(docs, genre_vehicule="MTL")
    assert r.is_valid
    assert len(r.errors) == 0
    assert len(r.documents_manquants) == 0


def test_dossier_complet_voiture_sans_ct():
    docs = _dossier_complet()
    r = validate_dossier(docs, genre_vehicule="VP")
    assert not r.is_valid  # CT manquant pour VP
    assert "controle_technique" in r.documents_manquants


def test_dossier_complet_voiture_avec_ct():
    docs = _dossier_complet()
    docs["controle_technique"] = {
        "resultat": "favorable",
        "date_limite_validite": "15/12/2026",
    }
    r = validate_dossier(docs, genre_vehicule="VP")
    assert r.is_valid


def test_vin_incoherent():
    docs = _dossier_complet()
    docs["certificat_cession"]["vin"] = "VF1RFB00X99999999"
    r = validate_dossier(docs, genre_vehicule="MTL")
    assert not r.is_valid
    assert any("VIN incohérent" in e for e in r.errors)


def test_immatriculation_incoherente():
    docs = _dossier_complet()
    docs["certificat_cession"]["immatriculation"] = "XY-999-ZZ"
    r = validate_dossier(docs, genre_vehicule="MTL")
    assert not r.is_valid
    assert any("Immatriculation incohérente" in e for e in r.errors)


def test_nom_incoherent():
    docs = _dossier_complet()
    docs["certificat_cession"]["acheteur_nom"] = "MARTIN"
    r = validate_dossier(docs, genre_vehicule="MTL")
    assert not r.is_valid
    assert any("Nom incohérent" in e for e in r.errors)


def test_justificatif_trop_ancien():
    docs = _dossier_complet()
    docs["justificatif_domicile"]["date_document"] = "01/01/2024"
    r = validate_dossier(docs, genre_vehicule="MTL")
    assert not r.is_valid
    assert any("trop ancien" in e for e in r.errors)


def test_cni_expiree():
    docs = _dossier_complet()
    docs["cni"]["date_validite"] = "01/01/2020"
    r = validate_dossier(docs, genre_vehicule="MTL")
    assert not r.is_valid
    assert any("expirée" in e for e in r.errors)


def test_document_manquant_cni():
    docs = _dossier_complet()
    del docs["cni"]
    r = validate_dossier(docs, genre_vehicule="MTL")
    assert not r.is_valid
    assert "cni" in r.documents_manquants


def test_ct_defavorable():
    docs = _dossier_complet()
    docs["controle_technique"] = {
        "resultat": "defavorable",
        "date_limite_validite": "15/12/2026",
    }
    r = validate_dossier(docs, genre_vehicule="VP")
    assert not r.is_valid


def test_fuzzy_match_identique():
    assert _fuzzy_match("DUPONT", "DUPONT")


def test_fuzzy_match_casse():
    assert _fuzzy_match("dupont", "DUPONT")


def test_fuzzy_match_contenu():
    assert _fuzzy_match("DUPONT", "DUPONT-MARTIN")


def test_fuzzy_match_typo():
    assert _fuzzy_match("DUPONT", "DUPONTT")  # 1 char de diff sur 7


def test_fuzzy_match_different():
    assert not _fuzzy_match("DUPONT", "MARTIN")


def test_parse_date_fr():
    d = _parse_date("15/03/2026")
    assert d is not None
    assert d.day == 15 and d.month == 3 and d.year == 2026


def test_parse_date_iso():
    d = _parse_date("2026-03-15")
    assert d is not None
    assert d.day == 15


def test_parse_date_invalid():
    assert _parse_date("pas une date") is None
    assert _parse_date("") is None


if __name__ == "__main__":
    for name, func in sorted(globals().items()):
        if name.startswith("test_") and callable(func):
            try:
                func()
                print(f"  ✓ {name}")
            except AssertionError as e:
                print(f"  ✗ {name}: {e}")
    print("Tests cross-checker terminés.")
