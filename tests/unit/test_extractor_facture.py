"""
Unit tests for FactureExtractor with synthetic OCR data.
Tests invoice/receipt extraction for vehicle purchase transactions.
"""
import pytest
from engine.extractors.facture import FactureExtractor


# Synthetic OCR for standard new vehicle invoice
FACTURE_NEUF_STANDARD_OCR = """
FACTURE DE VENTE
Numéro de facture : FAC-2026-0001234
Date : 15.04.2026

VENDEUR
AUTOMOBILES MARTIN S.A.R.L.
SIRET : 45678901234567
Adresse : 123, route de Nice
06000 NICE

ACHETEUR
Nom : DUPONT Michel
Adresse : 42, rue de la Paix
75010 PARIS

DÉTAIL DU VÉHICULE
VIN : WVW123456AB789012
Marque : Volkswagen
Modèle : Golf 8 Style
Énergie : Essence
Kilométrage : 0 km
État : Neuf

Prix HT : 28 500,00 €
TVA 20% : 5 700,00 €
Prix TTC : 34 200,00 €

Options et frais d'immatriculation compris.
Véhicule neuf direct de l'usine.

Signature vendeur

Conditions de paiement : À la signature du contrat d'achat
"""

# Synthetic OCR for used vehicle invoice
FACTURE_OCCASION_OCR = """
FACTURE DE VENTE - OCCASION

N° de facture : FAC-2026-0005678
Date : 10.04.2026

VENDEUR PROFESSIONNEL
GARAGE LEBLANC
SIRET : 56789012345678
Tél : 01.47.05.12.34
Adresse : 89, boulevard Saint-Germain
75006 PARIS

ACQUÉREUR
Monsieur/Mme : BERNARD Jean-Claude
Domicile : 15, avenue Montaigne
75008 PARIS

VÉHICULE
VIN : VSS9876543XY123456
Marque : Volvo
Modèle : V90 R-Design
Essence : Diesel
Kilométrage : 45 000 km

Prix HT : 32 000,00 €
TVA 20% : 6 400,00 €
Total TTC : 38 400,00 €

Révision faite. Garantie 6 mois.

Signature propriétaire précédent
Signature nouveau propriétaire
"""

# Synthetic OCR with vehicle specification details
FACTURE_DETAILS_TECHNIQUES_OCR = """
FACTURE AUTOMOBILE

Facture n° : INV/2026/000923
Date de vente : 22.04.2026

PROFESSIONNEL VENDEUR
Garage Prestige Autos
SIRET : 12345678901234
Siège : 200, rue de Rivoli, 75001 PARIS

CLIENT ACHETEUR
Madame MARTIN Sophie
Adresse livraison : 30, rue des Acacias, 13000 MARSEILLE

DÉTAILS VÉHICULE
VIN : WBA1234567CD890123
Marque : BMW
Modèle : Série 5
Type carrosserie : Berline 4 portes
Année modèle : 2026
Énergie : Hybride Électrique
Kilométrage initial : 10 km

Spécifications techniques :
- Puissance : 290 kW
- Cylindrée : 2000 cm³
- Consommation CO2 : 35 g/km

TARIFICATION
Prix catalogue : 58 000,00 €
Réductions appliquées : - 2 000,00 €
Prix net HT : 56 000,00 €
TVA 20% : 11 200,00 €
Prix de vente TTC : 67 200,00 €

Conditions : Paiement à réception
"""

# Synthetic OCR for pro-forma invoice (not final)
FACTURE_PRO_FORMA_OCR = """
PRO-FORMA INVOICE (NON-CONTRACTUELLE)

Numéro : PRO-2026-012345
Date : 18.04.2026
Validité : 7 jours

Vendeur : Concessionnaire BMW PARIS
SIRET : 98765432109876

Client : NOUVEAU Pierre
Adresse : 50, Champs-Élysées, 75008 PARIS

Véhicule
VIN : WBA5555555ZZ999999
Marque/Modèle : BMW X5 M50i

Prix TTC estimé : 95 000,00 €

Remarque : Ceci est une estimation. La facture définitive sera établie à la confirmation de commande.
Mention Pro-Forma
"""

# Synthetic OCR with corrupted/missing data
FACTURE_INCOMPLÈTE_OCR = """
FACTURE
N° : ???
Date : ??/??/2026

Vendeur : Garage [ILLEGIBLE]
SIRET : [MISSING]

Acheteur : ???

VIN : [ILLEGIBLE]
Marque : [Partiellement visible]

Prix : ???
"""

# Synthetic OCR with manual corrections (suspect)
FACTURE_CORRIGEE_MANUSCRITEMENT_OCR = """
FACTURE DE VENTE

N° facture : FAC-2026-001999
Date : 05.04.2026 [crossed out] 12.04.2026

Vendeur : AUTO SERVICES LYON
SIRET : 34567890123456

Client : ROUSSEAU Marc
Adresse : [handwritten correction: 25 rue Dumont instead of 10 rue Colbert]

VIN : WVW111222333444555
Marque : Volkswagen
Kilométrage : 0 km [handwritten: 25000 written over]
Prix TTC : 22 500 € [handwritten change to 19 500]

Signature vendeur
"""


class TestFactureExtractorNew:
    """Tests for new vehicle invoices."""

    @pytest.fixture
    def extractor(self):
        return FactureExtractor()

    def test_new_vehicle_invoice_extraction(self, extractor):
        """Test standard new vehicle invoice extraction."""
        result = extractor.extract(FACTURE_NEUF_STANDARD_OCR)
        assert result.success
        assert result.data["vin"] == "WVW123456AB789012"
        assert result.data["marque"] == "Volkswagen"
        assert result.data["modele"] == "Golf 8 Style"
        assert result.data["nom_vendeur"] == "AUTOMOBILES MARTIN S.A.R.L."
        assert result.data["siret_vendeur"] == "45678901234567"
        assert result.data["nom_acheteur"] == "DUPONT Michel"
        assert result.data["date_vente"] == "2026-04-15"
        assert result.confidence >= 0.85

    def test_new_vehicle_flag_detected(self, extractor):
        """Test that 'mention_neuf' is set correctly for new vehicles."""
        result = extractor.extract(FACTURE_NEUF_STANDARD_OCR)
        assert result.success
        assert result.data["mention_neuf"] is True
        assert result.data["kilometrage"] == 0

    def test_prices_extracted_correctly(self, extractor):
        """Test that HT and TTC prices are extracted."""
        result = extractor.extract(FACTURE_NEUF_STANDARD_OCR)
        assert result.success
        assert result.data["prix_ht"] == 28500.0
        assert result.data["prix_ttc"] == 34200.0
        assert result.data["tva_taux"] == 20


class TestFactureExtractorUsed:
    """Tests for used vehicle invoices."""

    @pytest.fixture
    def extractor(self):
        return FactureExtractor()

    def test_used_vehicle_invoice_extraction(self, extractor):
        """Test used vehicle invoice extraction."""
        result = extractor.extract(FACTURE_OCCASION_OCR)
        assert result.success
        assert result.data["vin"] == "VSS9876543XY123456"
        assert result.data["marque"] == "Volvo"
        assert result.data["kilometrage"] == 45000
        assert result.data["mention_neuf"] is False

    def test_used_vehicle_details_preserved(self, extractor):
        """Test that used vehicle details are correctly parsed."""
        result = extractor.extract(FACTURE_OCCASION_OCR)
        assert result.success
        assert result.data["prix_ttc"] == 38400.0
        assert "Diesel" in result.data["energie"] or "diesel" in result.data["energie"].lower()


class TestFactureExtractorValidation:
    """Tests for invoice validation logic."""

    @pytest.fixture
    def extractor(self):
        return FactureExtractor()

    def test_vin_format_17_chars(self, extractor):
        """Test that VIN is exactly 17 characters (cleaned)."""
        result = extractor.extract(FACTURE_NEUF_STANDARD_OCR)
        assert result.success
        vin = result.data["vin"].replace(" ", "").replace("-", "")
        assert len(vin) == 17

    def test_siret_14_digits(self, extractor):
        """Test that SIRET is 14 digits."""
        result = extractor.extract(FACTURE_NEUF_STANDARD_OCR)
        assert result.success
        siret = result.data["siret_vendeur"].replace(" ", "")
        assert len(siret) == 14
        assert siret.isdigit()

    def test_invoice_number_extraction(self, extractor):
        """Test that invoice number is extracted."""
        result = extractor.extract(FACTURE_NEUF_STANDARD_OCR)
        assert result.success
        assert result.data["n_facture"] is not None
        assert "FAC" in result.data["n_facture"] or "001234" in result.data["n_facture"]


class TestFactureExtractorErrors:
    """Tests for error handling."""

    @pytest.fixture
    def extractor(self):
        return FactureExtractor()

    def test_pro_forma_invoice_rejected(self, extractor):
        """Test that pro-forma invoices are flagged/rejected."""
        result = extractor.extract(FACTURE_PRO_FORMA_OCR)
        # Should either reject or flag as pro_forma
        assert result.data.get("pro_forma") is True or not result.success

    def test_incomplete_invoice_returns_error(self, extractor):
        """Test that incomplete invoice returns error."""
        result = extractor.extract(FACTURE_INCOMPLÈTE_OCR)
        assert not result.success
        assert len(result.errors) > 0

    def test_manual_corrections_flagged(self, extractor):
        """Test that manually corrected values lower confidence."""
        result = extractor.extract(FACTURE_CORRIGEE_MANUSCRITEMENT_OCR)
        # Should either reject or have very low confidence
        assert result.confidence < 0.6 or not result.success

    def test_missing_siret_error(self, extractor):
        """Test that missing SIRET is caught."""
        result = extractor.extract(FACTURE_INCOMPLÈTE_OCR)
        assert not result.success
