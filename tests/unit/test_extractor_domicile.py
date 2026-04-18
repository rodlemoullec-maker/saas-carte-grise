"""
Unit tests for DomicileExtractor with synthetic OCR data.
Tests proof of residence documents (utility bills, lease, bank statements, tax notices, etc).
"""
import pytest
from engine.extractors.domicile import DomicileExtractor


# Synthetic OCR for EDF electricity bill
EDF_BILL_OCR = """
Facture d'électricité
Numéro de client : 123456789
Date d'émission : 18.04.2026

Titulaire du contrat :
MOREAU Jean-Claude
15, rue de la Paix
75010 PARIS

Période de facturation : 15.03.2026 - 15.04.2026
Consommation : 287 kWh

Montant HT : 45,80 €
Montant TTC : 54,96 €

Date limite de paiement : 25.04.2026
"""

# Synthetic OCR for rent receipt (quittance de loyer)
QUITTANCE_LOYER_OCR = """
QUITTANCE DE LOYER
Année 2026 - Mois : AVRIL

Locataire : BERNARD Anne-Marie
Adresse : 42, avenue Victor Hugo
94200 IVRY-SUR-SEINE

Loyer brut : 650,00 €
Charges : 80,00 €
Loyer net : 650,00 €

Période couverte : 01.04.2026 - 30.04.2026
Date de quittance : 01.04.2026

Signature propriétaire/gestionnaire
"""

# Synthetic OCR for bank statement
RELEVE_BANCAIRE_OCR = """
RELEVÉ DE COMPTE
Banque Crédit Agricole
Compte n° : FR76 2000 3000 0000 0000 0000

Titulaire : DUPONT Michel
Adresse : 8, boulevard Haussmann
75008 PARIS

Période : 01.04.2026 - 30.04.2026
Édition : 30.04.2026

Solde initial : 2 456,78 €
Solde final : 3 120,45 €

Mouvements du mois (détails non affichés)
"""

# Synthetic OCR for tax assessment (avis d'imposition)
AVIS_IMPOSITION_OCR = """
AVIS D'IMPOSITION À LA SOURCE 2025
Année d'imposition : 2025

Contribuable : MARTIN Sophie
Domicile fiscal : 25, rue de la République
13000 MARSEILLE

Revenus déclarés : 35 000 €
Impôt sur le revenu : 4 200 €

Avis émis le : 15.03.2026
Mise en recouvrement : 15.04.2026

Référence dossier : 20260315001234
"""

# Synthetic OCR for housing attestation (attestation d'hébergement)
ATTESTATION_HEBERGEMENT_OCR = """
ATTESTATION D'HÉBERGEMENT

Je soussigné(e) : LEBLANC François
Domicilié(e) à : 10, rue du Faubourg Saint-Antoine
75012 PARIS

Atteste par la présente que :
NOUVEAU Pierre est hébergé(e) à mon domicile depuis le 01.01.2026

Je m'engage à signaler tout changement de situation.

Signé à Paris, le 15.04.2026
Signature

Pièce d'identité fournie : CNI n° 12345678
"""

# Synthetic OCR for Internet bill (facture Internet)
FACTURE_INTERNET_OCR = """
Facture Internet & Téléphone
Client : ROUSSEAU Éric
Adresse : 30, route de Versailles
78000 VERSAILLES

Numéro de facture : INV-2026-004521
Date d'émission : 10.04.2026

Internet 100 Mbps : 29,99 €
Téléphone fixe : 15,00 €
Adresse IP fixe (option) : 4,99 €

Total HT : 49,98 €
TVA 20% : 9,99 €
Total TTC : 59,97 €

À payer avant le 25.04.2026
"""

# Synthetic OCR with incomplete address
DOMICILE_ADRESSE_INCOMPLETE_OCR = """
Facture d'électricité
Date : 18.04.2026
Titulaire : THOMAS Isabelle
Adresse : N/A
Code postal : ????
Ville : INCONNU

Montant : 65,00 €
"""

# Synthetic OCR too old (not fresh enough)
FACTURE_TROP_ANCIENNE_OCR = """
Facture d'eau
Date d'émission : 15.01.2025
Titulaire : LECLERC Philippe
Adresse : 50, rue de Rivoli
75001 PARIS

Consommation : 125 m³
Montant : 98,50 €
"""


class TestDomicileExtractorUtilityBills:
    """Tests for utility bill extraction."""

    @pytest.fixture
    def extractor(self):
        return DomicileExtractor()

    def test_edf_bill_extraction(self, extractor):
        """Test EDF electricity bill extraction."""
        result = extractor.extract(EDF_BILL_OCR)
        assert result.success
        assert result.data["nom_titulaire"] == "MOREAU Jean-Claude"
        assert result.data["code_postal"] == "75010"
        assert result.data["ville"] == "PARIS"
        assert result.data["adresse_ligne1"] == "15, rue de la Paix"
        assert result.data["type_justificatif"] == "facture_electricite"
        assert result.data["date_document"] == "2026-04-18"
        assert result.confidence >= 0.8

    def test_internet_bill_extraction(self, extractor):
        """Test Internet/phone bill extraction."""
        result = extractor.extract(FACTURE_INTERNET_OCR)
        assert result.success
        assert result.data["nom_titulaire"] == "ROUSSEAU Éric"
        assert result.data["code_postal"] == "78000"
        assert result.data["ville"] == "VERSAILLES"
        assert result.data["type_justificatif"] == "facture_internet"

    def test_utility_bill_date_freshness(self, extractor):
        """Test that recent utility bill has high confidence."""
        result = extractor.extract(EDF_BILL_OCR)
        assert result.success
        # Recent document should have high confidence
        assert result.confidence >= 0.85

    def test_emetteur_extracted(self, extractor):
        """Test that utility company is identified."""
        result = extractor.extract(EDF_BILL_OCR)
        assert result.success
        assert result.data["emetteur"] is not None
        assert "EDF" in result.data["emetteur"] or "électricité" in result.data["emetteur"].lower()


class TestDomicileExtractorOtherDocs:
    """Tests for other proof of residence documents."""

    @pytest.fixture
    def extractor(self):
        return DomicileExtractor()

    def test_rent_receipt_extraction(self, extractor):
        """Test rent receipt (quittance de loyer) extraction."""
        result = extractor.extract(QUITTANCE_LOYER_OCR)
        assert result.success
        assert result.data["nom_titulaire"] == "BERNARD Anne-Marie"
        assert result.data["adresse_ligne1"] == "42, avenue Victor Hugo"
        assert result.data["code_postal"] == "94200"
        assert result.data["ville"] == "IVRY-SUR-SEINE"
        assert result.data["type_justificatif"] == "quittance_loyer"

    def test_bank_statement_extraction(self, extractor):
        """Test bank statement (relevé bancaire) extraction."""
        result = extractor.extract(RELEVE_BANCAIRE_OCR)
        assert result.success
        assert result.data["nom_titulaire"] == "DUPONT Michel"
        assert result.data["ville"] == "PARIS"
        assert result.data["type_justificatif"] == "releve_bancaire"

    def test_tax_notice_extraction(self, extractor):
        """Test tax assessment (avis d'imposition) extraction."""
        result = extractor.extract(AVIS_IMPOSITION_OCR)
        assert result.success
        assert result.data["nom_titulaire"] == "MARTIN Sophie"
        assert result.data["code_postal"] == "13000"
        assert result.data["ville"] == "MARSEILLE"
        assert result.data["type_justificatif"] == "avis_imposition"
        assert result.data["date_document"] == "2026-03-15"

    def test_housing_attestation_extraction(self, extractor):
        """Test housing attestation (attestation d'hébergement)."""
        result = extractor.extract(ATTESTATION_HEBERGEMENT_OCR)
        assert result.success
        # For attestation, hébergé name may be extracted as primary or secondary
        assert "LEBLANC" in result.data["nom_titulaire"] or "NOUVEAU" in result.data["nom_titulaire"]
        assert result.data["type_justificatif"] == "attestation_hebergement"


class TestDomicileExtractorErrors:
    """Tests for error handling."""

    @pytest.fixture
    def extractor(self):
        return DomicileExtractor()

    def test_incomplete_address_returns_error(self, extractor):
        """Test that incomplete address triggers error."""
        result = extractor.extract(DOMICILE_ADRESSE_INCOMPLETE_OCR)
        assert not result.success
        assert len(result.errors) > 0

    def test_old_document_rejected(self, extractor):
        """Test that document older than 3 months is marked as stale."""
        result = extractor.extract(FACTURE_TROP_ANCIENNE_OCR)
        # Could succeed with lower confidence or fail entirely
        assert result.confidence < 0.5 or not result.success

    def test_missing_postal_code_error(self, extractor):
        """Test that missing postal code is caught."""
        result = extractor.extract(DOMICILE_ADRESSE_INCOMPLETE_OCR)
        assert not result.success

    def test_country_defaults_to_france(self, extractor):
        """Test that country field defaults to 'France'."""
        result = extractor.extract(EDF_BILL_OCR)
        assert result.success
        assert result.data["pays"] == "France" or result.data["pays"] == "FR"
