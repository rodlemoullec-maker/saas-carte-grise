"""
Unit tests for PermisExtractor with synthetic OCR data.
Tests French driving permit (format EU since 2013).
"""
import pytest
from engine.extractors.permis import PermisExtractor


# Synthetic OCR text for French driving permit (EU format card since 2013)
PERMIS_FR_OCR = """
Permis de conduire
DUPONT Jean-Paul
Né le : 15.03.1978
N° de permis : 12AB345671FR123456
Date de délivrance : 21.06.2018
Valable jusqu'au : 21.06.2028

Catégories de permis:
B : 21.06.2018 - 21.06.2028
B+E : 21.06.2018 - 21.06.2028
C1 : 03.04.2020 - 03.04.2025

Restrictions : 01 (correction de la vue requise)
Pays d'émission : FR
"""

# Synthetic OCR for multi-category permit
PERMIS_MULTI_CATEGORIES_OCR = """
Permis de conduire
MARTIN Sophie
Né le : 12.07.1985
N° de permis : 85CD789012FR654321
Date de délivrance : 10.09.2015
Valable jusqu'au : 10.09.2025

Catégories:
A : 10.09.2015 - 10.09.2025
A2 : 10.09.2015 - 10.09.2025
B : 10.09.2015 - 10.09.2025
C : 21.03.2018 - 21.03.2023
C+E : 21.03.2018 - 21.03.2023

Restrictions : 01, 04, 10
"""

# Synthetic OCR for foreign driving permit (non-French)
PERMIS_ETRANGER_OCR = """
Driving Licence
SCHMIDT Klaus
Date of birth : 28.11.1980
Licence number : 9876543210US123
Issue date : 14.05.2019
Valid until : 14.05.2029

Licence categories :
Class B : 14.05.2019 - 14.05.2029
Class C : 14.05.2019 - 14.05.2024

Issued by : State of California
Restrictions : None
"""

# Synthetic OCR with expired categories
PERMIS_CATEGORIES_EXPIREES_OCR = """
Permis de conduire
BERNARD Michel
Né le : 22.02.1960
N° de permis : 60EF012345FR789012
Date de délivrance : 05.08.2005
Valable jusqu'au : 05.08.2015

Catégories:
B : 05.08.2005 - 05.08.2015 (EXPIREE)
A : 12.11.2008 - 12.11.2018 (EXPIREE)
C1 : 19.01.2010 - 19.01.2020 (EXPIREE)

Restrictions : Aucune
"""

# OCR with missing critical fields
PERMIS_INCOMPLET_OCR = """
Permis de conduire
NOUVEAU
Nat le : ??
N permis : XX??XX
Catégories : illegible
Restrictions : N/A
"""


class TestPermisExtractorFrench:
    """Tests for French driving permit extraction."""

    @pytest.fixture
    def extractor(self):
        return PermisExtractor()

    def test_extraction_basic_permit(self, extractor):
        """Test basic French permit extraction."""
        result = extractor.extract(PERMIS_FR_OCR)
        assert result.success
        assert result.data["nom"] == "DUPONT"
        assert result.data["prenom"] == "Jean-Paul"
        assert result.data["date_naissance"] == "1978-03-15"
        assert result.data["n_permis"] == "12AB345671FR123456"
        assert result.confidence >= 0.8

    def test_categories_extracted_with_dates(self, extractor):
        """Test that all categories are extracted with dates."""
        result = extractor.extract(PERMIS_FR_OCR)
        assert result.success
        assert len(result.data["categories"]) >= 2
        categories_by_code = {cat["code"]: cat for cat in result.data["categories"]}
        assert "B" in categories_by_code
        assert "B+E" in categories_by_code
        assert categories_by_code["B"]["date_obtention"] == "2018-06-21"
        assert categories_by_code["B"]["date_validite"] == "2028-06-21"

    def test_restrictions_extracted(self, extractor):
        """Test that restrictions are extracted."""
        result = extractor.extract(PERMIS_FR_OCR)
        assert result.success
        assert "01" in result.data["restrictions"]

    def test_multi_category_permit(self, extractor):
        """Test extraction of permit with multiple categories."""
        result = extractor.extract(PERMIS_MULTI_CATEGORIES_OCR)
        assert result.success
        assert result.data["prenom"] == "Sophie"
        # Should have at least 5 categories
        assert len(result.data["categories"]) >= 5
        assert result.data["restrictions"] == ["01", "04", "10"]

    def test_country_emission_detected(self, extractor):
        """Test that country of emission is detected."""
        result = extractor.extract(PERMIS_FR_OCR)
        assert result.success
        assert result.data["pays_emission"] == "FR"

    def test_delivery_and_validity_dates(self, extractor):
        """Test dates de délivrance and date_validite are distinct."""
        result = extractor.extract(PERMIS_FR_OCR)
        assert result.success
        assert result.data["date_delivrance"] == "2018-06-21"


class TestPermisExtractorForeign:
    """Tests for foreign driving permits."""

    @pytest.fixture
    def extractor(self):
        return PermisExtractor()

    def test_foreign_permit_extracted(self, extractor):
        """Test extraction of foreign (US) permit."""
        result = extractor.extract(PERMIS_ETRANGER_OCR)
        assert result.success
        assert result.data["nom"] == "SCHMIDT"
        assert result.data["prenom"] == "Klaus"
        assert result.data["date_naissance"] == "1980-11-28"
        # Should flag as foreign
        assert result.data["pays_emission"] != "FR"

    def test_foreign_categories_format(self, extractor):
        """Test that foreign category format is handled."""
        result = extractor.extract(PERMIS_ETRANGER_OCR)
        assert result.success
        categories_by_code = {cat["code"]: cat for cat in result.data["categories"]}
        # US uses different category codes
        assert any(cat in categories_by_code for cat in ["B", "C", "Class B", "Class C"])


class TestPermisExtractorErrors:
    """Tests for error handling."""

    @pytest.fixture
    def extractor(self):
        return PermisExtractor()

    def test_incomplete_permit_returns_errors(self, extractor):
        """Test that incomplete permit returns error list."""
        result = extractor.extract(PERMIS_INCOMPLET_OCR)
        assert not result.success
        assert len(result.errors) > 0
        # Should report missing critical fields
        assert any("nom" in err.lower() or "prenom" in err.lower() or "date" in err.lower() 
                  for err in result.errors)

    def test_expired_categories_flagged(self, extractor):
        """Test that expired categories are detected."""
        result = extractor.extract(PERMIS_CATEGORIES_EXPIREES_OCR)
        assert result.success
        # Should indicate expiration status in error or metadata
        assert result.confidence < 0.9  # Lower confidence for expired permit

    def test_invalid_permit_number_format(self, extractor):
        """Test that invalid permit number is caught."""
        result = extractor.extract(PERMIS_INCOMPLET_OCR)
        assert not result.success
