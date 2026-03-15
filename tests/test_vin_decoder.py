"""Tests du décodeur VIN."""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.vehicle.vin_decoder import decode_vin, is_valid_vin


def test_valid_vin():
    assert is_valid_vin("WBA11AG01MCF12345")
    assert is_valid_vin("VF1RFB00X12345678")
    assert is_valid_vin("JYARN491000012345")


def test_invalid_vin():
    assert not is_valid_vin("")
    assert not is_valid_vin("ABC")
    assert not is_valid_vin("WBAIIAG01MCF1234")   # 16 chars
    # Note: "12345678901234567" (17 digits) EST valide syntaxiquement


def test_invalid_chars_vin():
    # I, O, Q ne sont pas autorisés dans un VIN
    assert not is_valid_vin("WBA11AG0IMCF12345")  # I
    assert not is_valid_vin("WBA11AG0OMCF12345")  # O
    assert not is_valid_vin("WBA11AG0QMCF12345")  # Q


def test_decode_bmw():
    result = decode_vin("WBA11AG01MCF12345")
    assert result["constructeur"] == "BMW"
    assert result["pays_origine"] == "Allemagne"
    assert result["annee_modele"] == 2021  # M = 2021


def test_decode_renault():
    result = decode_vin("VF1RFB00X12345678")
    assert result["constructeur"] == "Renault"
    assert result["pays_origine"] == "France"


def test_decode_yamaha():
    result = decode_vin("JYARN491000012345")
    assert result["constructeur"] == "Yamaha"
    assert result["pays_origine"] == "Japon"


def test_decode_unknown_wmi():
    result = decode_vin("ZZZZZZZZZZZZZZZZZ")
    assert result["constructeur"] == "Inconnu" or "error" not in result


def test_decode_invalid():
    result = decode_vin("ABC")
    assert "error" in result


if __name__ == "__main__":
    for name, func in list(globals().items()):
        if name.startswith("test_") and callable(func):
            try:
                func()
                print(f"  ✓ {name}")
            except AssertionError as e:
                print(f"  ✗ {name}: {e}")
    print("Tests VIN decoder terminés.")
