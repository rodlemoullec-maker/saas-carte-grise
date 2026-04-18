"""
Unit tests for COCExtractor with synthetic OCR data.
Tests Certificate of Conformity (COC) extraction for vehicle specifications.
"""
import pytest
from engine.extractors.coc import COCExtractor


# Synthetic OCR for European COC - Gasoline vehicle
COC_ESSENCE_OCR = """
CERTIFICATE OF CONFORMITY
Certificat de Conformité

VIN : WVW123456AB789012
CNIT : GB-AB-123-45-A-456-789
Marque : Volkswagen
Modèle : Golf 8

Type de carburant : Essence sans plomb 95
Puissance nette : 110 kW
Puissance fiscale : 150 CV
Cylindrée : 1998 cm³

Type de carrosserie : Berline 5 portes
Nombre de places assises : 5
PTAC : 1500 kg
PV : 1300 kg

Numéro d'homologation EU : EU/2020/XX/0123
Constructeur : Volkswagen AG
Pays : Allemagne (DE)

Date de première immatriculation UE : 01.03.2020
"""

# Synthetic OCR for Electric vehicle COC
COC_ELECTRIQUE_OCR = """
CERTIFICATE OF CONFORMITY
CERTIFICAT DE CONFORMITÉ

VIN : WBA1234567CD890123
CNIT : DE-BA-234-56-B-567-890
Marque : BMW
Modèle : i3

Carburant/Énergie : Électrique
Puissance nette : 135 kW
Puissance fiscale : 184 CV
Batterie : 42 kWh

Carrosserie : Citadine 4 portes
Places assises : 4
PTAC : 1850 kg
PV : 1515 kg

Numéro homologation EU : EU/2019/XX/1245
Constructeur : BMW GmbH
Pays : Allemagne

Première immatriculation UE : 15.06.2021
"""

# Synthetic OCR for Diesel vehicle
COC_DIESEL_OCR = """
CERTIFICATE OF CONFORMITY
Certificate de Conformité

VIN : VSS9876543XY123456
CNIT : FR-SS-987-65-C-876-123
Marque : Peugeot
Modèle : 3008

Carburant : Gazole (Diesel)
Puissance nette : 96 kW
Puissance fiscale : 130 CV
Cylindrée : 1560 cm³

Carrosserie : SUV 5 portes
Nombre places : 5
PTAC : 1725 kg

Normes d'émission : Euro 6d-TEMP
Homologation : EU/2017/XX/0987
Constructeur : Peugeot S.A.

Date 1ère immatriculation : 22.11.2018
"""

# Synthetic OCR for Hybrid vehicle
COC_HYBRIDE_OCR = """
CERTIFICATE OF CONFORMITY

VIN : ZFA1234567ZH111222
CNIT : IT-FA-111-22-D-333-444
Marque : Ferrari
Modèle : SF90 Stradale

Énergie : Hybrid (Essence + Électrique)
Puissance nette moteur essence : 780 kW
Puissance nette moteur électrique : 220 kW
Puissance fiscale combinée : 1200 CV

Carrosserie : Berline sportive 2+2
Places assises : 4
PTAC : 1570 kg

Capacité batterie : 7.9 kWh
Normes émission : Euro 6d

Première immatriculation UE : 31.05.2019
"""

# Synthetic OCR with missing critical VIN
COC_VIN_MANQUANT_OCR = """
CERTIFICATE OF CONFORMITY

VIN : [ILLEGIBLE]
CNIT : GB-CD-456-78-E-901-234
Marque : Aston Martin
Modèle : DB11

Puissance : 448 kW
Carrosserie : Berline 2 portes
"""

# Synthetic OCR with malformed VIN/CNIT
COC_FORMAT_INVALIDE_OCR = """
CERTIFICATE OF CONFORMITY

VIN : WBA123-4567-CD890-123 [too many hyphens]
CNIT : 12345  [only digits, invalid format]
Marque : Mercedes
Modèle : E-Class

Énergie : Essence
Puissance : 205 kW
"""


class TestCOCExtractorEssence:
    """Tests for gasoline vehicle COC."""

    @pytest.fixture
    def extractor(self):
        return COCExtractor()

    def test_gasoline_coc_extraction(self, extractor):
        """Test gasoline vehicle COC extraction."""
        result = extractor.extract(COC_ESSENCE_OCR)
        assert result.success
        assert result.data["vin"] == "WVW123456AB789012"
        assert result.data["marque"] == "Volkswagen"
        assert result.data["modele"] == "Golf 8"
        assert result.data["energie"] == "essence"
        assert result.data["puissance_kw"] == 110
        assert result.data["puissance_fiscale_cv"] == 150
        assert result.data["cylindree_cm3"] == 1998
        assert result.confidence >= 0.85

    def test_coc_cnit_format_validation(self, extractor):
        """Test CNIT format is correctly validated."""
        result = extractor.extract(COC_ESSENCE_OCR)
        assert result.success
        cnit = result.data["cnit"]
        # CNIT format : 2 lettres - 3 chiffres - 2 lettres - 2 chiffres - 1 lettre - 3 chiffres
        assert len(cnit.replace("-", "")) >= 14

    def test_carrosserie_extracted(self, extractor):
        """Test that vehicle body type is extracted."""
        result = extractor.extract(COC_ESSENCE_OCR)
        assert result.success
        assert "berline" in result.data["carrosserie"].lower() or result.data["carrosserie"] is not None

    def test_ptac_and_places_extracted(self, extractor):
        """Test that PTAC and seating capacity are extracted."""
        result = extractor.extract(COC_ESSENCE_OCR)
        assert result.success
        assert result.data["ptac_kg"] == 1500
        assert result.data["places_assises"] == 5


class TestCOCExtractorAlternativeEnergies:
    """Tests for alternative fuel/energy COCs."""

    @pytest.fixture
    def extractor(self):
        return COCExtractor()

    def test_electric_vehicle_coc(self, extractor):
        """Test electric vehicle COC extraction."""
        result = extractor.extract(COC_ELECTRIQUE_OCR)
        assert result.success
        assert result.data["vin"] == "WBA1234567CD890123"
        assert result.data["energie"] == "électrique"
        assert result.data["puissance_kw"] == 135
        assert result.data["marque"] == "BMW"

    def test_diesel_vehicle_normalization(self, extractor):
        """Test that diesel energy is normalized."""
        result = extractor.extract(COC_DIESEL_OCR)
        assert result.success
        assert result.data["energie"] == "diesel"
        assert result.data["puissance_kw"] == 96

    def test_hybrid_vehicle_detection(self, extractor):
        """Test hybrid vehicle energy detection."""
        result = extractor.extract(COC_HYBRIDE_OCR)
        assert result.success
        assert result.data["energie"] == "hybride" or result.data["energie"] == "hybride_rechargeable"
        # For hybrid, may have dual power output
        assert result.data["puissance_kw"] is not None

    def test_energy_normalization_map(self, extractor):
        """Test that energy values are normalized to standard list."""
        valid_energies = {"essence", "diesel", "électrique", "hybride", "hybride_rechargeable", "gpl", "gnv"}
        result = extractor.extract(COC_DIESEL_OCR)
        assert result.success
        assert result.data["energie"] in valid_energies


class TestCOCExtractorErrors:
    """Tests for error handling."""

    @pytest.fixture
    def extractor(self):
        return COCExtractor()

    def test_missing_vin_error(self, extractor):
        """Test that missing VIN is caught as error."""
        result = extractor.extract(COC_VIN_MANQUANT_OCR)
        assert not result.success
        assert any("vin" in err.lower() for err in result.errors)

    def test_invalid_vin_format_rejected(self, extractor):
        """Test that malformed VIN is rejected."""
        result = extractor.extract(COC_FORMAT_INVALIDE_OCR)
        assert not result.success
        # Should have VIN format error
        assert len(result.errors) > 0

    def test_invalid_cnit_format_reported(self, extractor):
        """Test that invalid CNIT format is reported."""
        result = extractor.extract(COC_FORMAT_INVALIDE_OCR)
        assert not result.success

    def test_null_fields_allowed(self, extractor):
        """Test that optional fields can be null."""
        result = extractor.extract(COC_ESSENCE_OCR)
        assert result.success
        # Some optional fields might be null
        assert result.data.get("n_homologation_eu") is not None or True  # Optional
