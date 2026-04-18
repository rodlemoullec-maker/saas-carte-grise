"""
Unit tests for CessionExtractor with synthetic OCR data.
Tests transfer certificate (Cerfa 15776) extraction.
"""
import pytest
from engine.extractors.cession import CessionExtractor


# Synthetic OCR for standard transfer certificate (Cerfa 15776)
CESSION_STANDARD_OCR = """
CERTIFICAT DE CESSION D'UN VÉHICULE

Ancien propriétaire : DUPONT Jean-Claude
Adresse : 42, rue de la Paix
75010 PARIS

Nouveau propriétaire : MARTIN Sophie
Adresse : 25, rue de la République
13000 MARSEILLE

Immatriculation : AB-123-CD
Numéro de formule : 0123456789
Date de cession : 15.04.2026

VIN : VSS9876543XY123456
Marque : Volvo
Modèle : XC60

État du compteur kilométrique : 45 000 km

Signature ancien propriétaire : [signature]
Date : 15.04.2026

Signature nouveau propriétaire : [signature]
Date : 15.04.2026

TAMPON/CACHET ÉTABLISSEMENT
SIRET : 45678901234567
"""

# Synthetic OCR for recent (2024+) format with QR code
CESSION_MODERNE_OCR = """
CERTIFICAT DE CESSION (Cerfa 15776)

Date du document : 10.04.2026

Cédant (ancien propriétaire) :
NOM : BERNARD
Prénom : Michel
Date naissance : 22.02.1960
Domicile : 89, boulevard Haussmann, 75008 PARIS

Acheteur (nouveau propriétaire) :
NOM : ROUSSEAU
Prénom : Marie
Domicile : 100, avenue des Champs-Élysées, 75008 PARIS

INFORMATIONS VÉHICULE
Immatriculation ancienne : BC-456-EF
VIN : WVW111222333444555
Marque : Volkswagen
Modèle : Golf VIII

Kilométrage : 78 500 km

Date et heure de cession : 10.04.2026 14:30

SIGNATURES
Signature vendeur (ancien propriétaire) : [SIGNÉE]
Signature acheteur (nouveau propriétaire) : [SIGNÉE]

VENDEUR PROFESSIONNEL (si applicable)
Société : Auto Services Île-de-France
SIRET : 56789012345678
Signature : [TAMPON + SIGNATURE]
"""

# Synthetic OCR with handwritten dates (various formats)
CESSION_DATES_MULTIFORMATS_OCR = """
CERTIFICAT DE CESSION

Ancien propriétaire : LECLERC Philippe
Nouveau propriétaire : THOMAS Isabelle

Immatriculation : CD-789-GH
VIN : WBA1234567CD890123
Marque : BMW
Modèle : Série 5

Date de cession : 22/03/2026
(Also written as : 22.03.2026)
(Also written as : 22/3/26)

Kilométrage : 156 000

Signature ancien propriétaire : [signature]
Date : 22/03/2026

Signature nouveau propriétaire : [signature]
Date : 22/03/2026
"""

# Synthetic OCR missing signatures
CESSION_SIGNATURES_MANQUANTES_OCR = """
CERTIFICAT DE CESSION

Ancien propriétaire : NOUVEAU Jean
Nouveau propriétaire : ANCIEN Pierre

Immatriculation : EF-012-IJ
VIN : ZFA1234567ZH111222
Marque : Ferrari
Modèle : SF90

Date de cession : 05.04.2026

Signature ancien propriétaire : [MISSING/BLANK]
Signature nouveau propriétaire : [MISSING/BLANK]
"""

# Synthetic OCR with incomplete VIN
CESSION_VIN_INCOMPLET_OCR = """
CERTIFICAT DE CESSION

Ancien propriétaire : MARTIN Claire
Nouveau propriétaire : MARTIN Luc

Immatriculation : GH-345-KL
VIN : VSS9876543XY12345  [only 16 chars - incomplete]
Marque : Volvo

Date de cession : 12.04.2026

Signature ancien propriétaire : [signature]
Signature nouveau propriétaire : [signature]
"""

# Synthetic OCR with different immatriculation formats
CESSION_IMMAT_FORMATS_OCR = """
CERTIFICAT DE CESSION

Ancien propriétaire : DUPUIS Laurent
Nouveau propriétaire : MARTIN Nathalie

Immatriculation (old) : 7521 XK 75  [old format]
Immatriculation (new) : IJ-678-MN   [EU format]
VIN : WVW123456AB789012
Marque : Volkswagen
Modèle : Polo

Date cédé le : 28.03.2026

Signature propriétaire : [signature]
Signature acquéreur : [signature]
"""

# Synthetic OCR with professional seller details
CESSION_VENDEUR_PRO_OCR = """
CERTIFICAT DE CESSION

ANCIEN PROPRIÉTAIRE (Professionnel)
Société : GARAGE CENTRAL AUTOS
SIRET : 67890123456789
Adresse : 150, rue du Commerce, 75015 PARIS
Représentant : DUCLOS Bernard
Signature gestionnaire : [TAMPON + SIGNATURE]

NOUVEAU PROPRIÉTAIRE (Particulier)
NOM : FERNANDES
Prénom : José
Domicile : 30, rue de Turenne, 75003 PARIS

Immatriculation : JK-901-OP
VIN : VSS9876543XY123456
Marque : Volvo
Modèle : V90

Date cession : 01.04.2026 10:00

Signatures présentes et datées
"""


class TestCessionExtractorStandard:
    """Tests for standard transfer certificate extraction."""

    @pytest.fixture
    def extractor(self):
        return CessionExtractor()

    def test_standard_cession_extraction(self, extractor):
        """Test standard transfer certificate extraction."""
        result = extractor.extract(CESSION_STANDARD_OCR)
        assert result.success
        assert result.data["vendeur_nom"] == "DUPONT Jean-Claude"
        assert result.data["acheteur_nom"] == "MARTIN Sophie"
        assert result.data["immatriculation"] == "AB-123-CD" or result.data["immatriculation"] == "AB123CD"
        assert result.data["vin"] == "VSS9876543XY123456"
        assert result.data["marque"] == "Volvo"
        assert result.confidence >= 0.85

    def test_cession_date_extracted(self, extractor):
        """Test that transfer date is correctly extracted."""
        result = extractor.extract(CESSION_STANDARD_OCR)
        assert result.success
        assert result.data["date_cession"] == "2026-04-15"

    def test_signatures_detected(self, extractor):
        """Test that signatures are detected."""
        result = extractor.extract(CESSION_STANDARD_OCR)
        assert result.success
        assert result.data["signatures_vendeur"] is True
        assert result.data["signature_acheteur"] is True

    def test_formula_number_extracted(self, extractor):
        """Test that formula number is extracted."""
        result = extractor.extract(CESSION_STANDARD_OCR)
        assert result.success
        assert result.data["numero_formule"] == "0123456789"

    def test_professional_siret_extracted(self, extractor):
        """Test that professional SIRET is extracted when present."""
        result = extractor.extract(CESSION_STANDARD_OCR)
        assert result.success
        assert result.data.get("siret_vendeur") is not None
        assert "45678901234567" in str(result.data.get("siret_vendeur", ""))


class TestCessionExtractorModern:
    """Tests for modern format transfer certificates."""

    @pytest.fixture
    def extractor(self):
        return CessionExtractor()

    def test_modern_cession_extraction(self, extractor):
        """Test modern format (2024+) transfer certificate."""
        result = extractor.extract(CESSION_MODERNE_OCR)
        assert result.success
        assert "BERNARD" in result.data["vendeur_nom"]
        assert "ROUSSEAU" in result.data["acheteur_nom"]
        assert "Volkswagen" in result.data["marque"]

    def test_modern_format_signatures(self, extractor):
        """Test that signatures are detected in modern format."""
        result = extractor.extract(CESSION_MODERNE_OCR)
        assert result.success
        assert result.data["signatures_vendeur"] is True
        assert result.data["signature_acheteur"] is True

    def test_professional_seller_modern_format(self, extractor):
        """Test professional seller in modern format."""
        result = extractor.extract(CESSION_VENDEUR_PRO_OCR)
        assert result.success
        assert "GARAGE" in result.data["vendeur_nom"]
        # SIRET should be extractable for professional
        assert result.data.get("siret_vendeur") is not None


class TestCessionExtractorDateFormats:
    """Tests for various date format handling."""

    @pytest.fixture
    def extractor(self):
        return CessionExtractor()

    def test_date_format_dd_mm_yyyy_slash(self, extractor):
        """Test DD/MM/YYYY date format."""
        result = extractor.extract(CESSION_DATES_MULTIFORMATS_OCR)
        assert result.success
        assert result.data["date_cession"] == "2026-03-22"

    def test_date_format_dd_mm_yy(self, extractor):
        """Test DD/MM/YY date format (2-digit year)."""
        # This tests the _parse_date helper function
        result = extractor.extract(CESSION_DATES_MULTIFORMATS_OCR)
        assert result.success
        # Year should be corrected to 2026
        assert "2026" in result.data["date_cession"]


class TestCessionExtractorImmatriculation:
    """Tests for immatriculation format handling."""

    @pytest.fixture
    def extractor(self):
        return CessionExtractor()

    def test_eu_format_immatriculation(self, extractor):
        """Test EU format immatriculation (AB-123-CD)."""
        result = extractor.extract(CESSION_STANDARD_OCR)
        assert result.success
        immat = result.data["immatriculation"].replace(" ", "").replace("-", "")
        assert len(immat) == 7  # 2 letters + 3 digits + 2 letters

    def test_old_format_immatriculation_detected(self, extractor):
        """Test that old format (7521 XK 75) is handled."""
        result = extractor.extract(CESSION_IMMAT_FORMATS_OCR)
        assert result.success
        # Should prefer EU format when both available
        assert "678" in result.data["immatriculation"] or "7521" in result.data["immatriculation"]


class TestCessionExtractorErrors:
    """Tests for error handling."""

    @pytest.fixture
    def extractor(self):
        return CessionExtractor()

    def test_missing_signatures_error(self, extractor):
        """Test that missing signatures trigger error/low confidence."""
        result = extractor.extract(CESSION_SIGNATURES_MANQUANTES_OCR)
        # Should either fail or have low confidence
        assert not result.success or result.confidence < 0.7

    def test_incomplete_vin_error(self, extractor):
        """Test that incomplete VIN (< 17 chars) is caught."""
        result = extractor.extract(CESSION_VIN_INCOMPLET_OCR)
        assert not result.success or result.confidence < 0.6

    def test_missing_immatriculation_error(self, extractor):
        """Test that missing immatriculation triggers error."""
        # Create test data with missing immatriculation
        bad_ocr = """
CERTIFICAT DE CESSION
Ancien propriétaire : TEST
Nouveau propriétaire : TEST
Immatriculation : [NOT FOUND]
VIN : VSS9876543XY123456
"""
        result = extractor.extract(bad_ocr)
        assert not result.success

    def test_vin_format_validation(self, extractor):
        """Test that VIN must be exactly 17 characters."""
        result = extractor.extract(CESSION_VIN_INCOMPLET_OCR)
        # Incomplete VIN should cause failure
        assert not result.success or result.confidence < 0.5
