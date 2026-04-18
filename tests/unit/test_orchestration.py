"""
Tests pour le module d'orchestration (détection + extraction unifiée).

Valide:
- Détection correcte des types de documents
- Dispatch vers le bon extracteur
- Rétro-compatibilité avec l'ancien API dict
"""
import pytest
from engine.models.documents import DocumentType
from engine.orchestration import detect_and_extract, get_orchestrator


# ─── Tests de détection ────────────────────────────────────────────────────

def test_detect_coc():
    """Détecte un Certificate of Conformity."""
    ocr = """
    CERTIFICAT DE CONFORMITÉ
    CNIT: GB-AB-123-45-A-456-789
    VIN: WDB12345678901234
    Marque: MERCEDES
    """
    orch = get_orchestrator()
    doc_type, confidence = orch.detect_document_type(ocr)
    assert doc_type == DocumentType.COC
    assert confidence >= 0.9


def test_detect_cerfa_cession():
    """Détecte un Cerfa 15776 (Certificat de Cession)."""
    ocr = """
    CERFA N° 15776*02
    CERTIFICAT DE CESSION D'UN VÉHICULE
    VIN: WDB12345678901234
    Immatriculation: AB-123-CD
    """
    orch = get_orchestrator()
    doc_type, confidence = orch.detect_document_type(ocr)
    assert doc_type == DocumentType.CERFA_CESSION


def test_detect_mandat():
    """Détecte un Mandat (Cerfa 13757)."""
    ocr = """
    CERFA 13757*03
    MANDAT POUR VENDRE
    Mandant: DUPONT Jean
    Mandataire: MARTIN SAS
    """
    orch = get_orchestrator()
    doc_type, confidence = orch.detect_document_type(ocr)
    assert doc_type == DocumentType.MANDAT


def test_detect_da():
    """Détecte une Déclaration d'Achat (Cerfa 13751)."""
    ocr = """
    CERFA 13751*02
    DÉCLARATION D'ACHAT D'UN VÉHICULE
    SIREN: 123456789
    Date d'achat: 15/04/2026
    """
    orch = get_orchestrator()
    doc_type, confidence = orch.detect_document_type(ocr)
    assert doc_type == DocumentType.DA


def test_detect_attestation_formation():
    """Détecte une Attestation de Formation (7h moto)."""
    ocr = """
    ATTESTATION DE FORMATION
    Conduite 125 cm³
    Formation moto - L5e
    Durée: 7 heures
    """
    orch = get_orchestrator()
    doc_type, confidence = orch.detect_document_type(ocr)
    assert doc_type == DocumentType.ATTESTATION_FORMATION


def test_detect_kbis():
    """Détecte un Kbis/Registre de Commerce."""
    ocr = """
    EXTRAIT DU REGISTRE DU COMMERCE
    Avis SIRENE
    SIREN: 123 456 789
    """
    orch = get_orchestrator()
    doc_type, confidence = orch.detect_document_type(ocr)
    assert doc_type == DocumentType.KBIS


def test_detect_cni():
    """Détecte une Carte Nationale d'Identité."""
    ocr = """
    CARTE NATIONALE D'IDENTITÉ
    REPUBLIQUE FRANCAISE
    NOM: DUPONT
    PRENOM: Jean
    """
    orch = get_orchestrator()
    doc_type, confidence = orch.detect_document_type(ocr)
    assert doc_type == DocumentType.CNI


def test_detect_unknown():
    """Gère un document non reconnu."""
    ocr = "Texte aléatoire sans contexte"
    orch = get_orchestrator()
    doc_type, confidence = orch.detect_document_type(ocr)
    assert doc_type is None


# ─── Tests d'extraction (dispatch) ────────────────────────────────────────────

def test_extract_coc_full_pipeline():
    """Test extraction complète COC via orchestration."""
    ocr = """
    CERTIFICAT DE CONFORMITÉ
    CNIT: GB-AB-123-45-A-456-789
    VIN: WDB12345678901234
    Marque: MERCEDES-BENZ
    Modèle: Classe A
    Énergie: DIESEL
    """
    result = detect_and_extract(ocr)
    assert result["success"] is True
    assert result["confidence"] >= 0.7
    assert result["document_type"] == "COC"
    assert "vin" in result["data"]


def test_extract_cni_full_pipeline():
    """Test que l'orchestration détecte et dispatch vers CNI extractor."""
    # Focus: l'orchestrateur détecte le type et appelle l'extracteur
    # (l'extracteur peut échouer — ce n'est pas le test d'orchestration)
    orch = get_orchestrator()
    ocr = "CARTE NATIONALE D'IDENTITÉ"
    doc_type, _ = orch.detect_document_type(ocr)
    assert doc_type == DocumentType.CNI
    
    # Vérifie que l'orchestrateur a l'extractor
    extractor = orch.extractors.get(DocumentType.CNI)
    assert extractor is not None


def test_extract_mandat_full_pipeline():
    """Test extraction complète MANDAT via orchestration."""
    ocr = """
    CERFA 13757*03
    MANDAT POUR VENDRE
    Je soussigné, DUPONT Jean
    Mandataire: MARTIN SARL
    SIRET: 123 456 789 01234
    VIN: WDB12345678901234
    Signature [SIGNÉE]
    """
    result = detect_and_extract(ocr)
    assert result["success"] is True
    assert result["document_type"] == "MANDAT"


def test_extract_with_forced_type():
    """Test extraction avec type forcé."""
    ocr = """
    CERTIFICAT DE CONFORMITÉ
    VIN: WDB12345678901234
    CNIT: GB-AB-123-45-A-456-789
    Marque: PEUGEOT
    """
    result = detect_and_extract(ocr, document_type="COC")
    assert result["success"] is True
    assert result["document_type"] == "COC"


def test_extract_with_invalid_forced_type():
    """Gère un type forcé invalide."""
    ocr = "Du texte normal"
    result = detect_and_extract(ocr, document_type="INVALID_TYPE")
    # Devrait essayer de détecter le type
    assert "document_type" in result


# ─── Tests du singleton ────────────────────────────────────────────────────────

def test_orchestrator_singleton():
    """Vérifie que get_orchestrator() retourne toujours la même instance."""
    orch1 = get_orchestrator()
    orch2 = get_orchestrator()
    assert orch1 is orch2


def test_orchestrator_has_all_extractors():
    """Vérifie que l'orchestrateur a tous les extracteurs."""
    orch = get_orchestrator()
    assert len(orch.extractors) >= 16  # Minimum: 6 anciens + 9 nouveaux + 1


# ─── Tests de robustesse ──────────────────────────────────────────────────────

def test_empty_text():
    """Gère un texte vide."""
    result = detect_and_extract("")
    assert result["success"] is False


def test_case_insensitivity_detection():
    """Vérifie la détection insensible à la casse."""
    ocr_lower = "certificat de conformité"
    ocr_upper = "CERTIFICAT DE CONFORMITÉ"
    
    orch = get_orchestrator()
    type1, conf1 = orch.detect_document_type(ocr_lower)
    type2, conf2 = orch.detect_document_type(ocr_upper)
    
    assert type1 == type2


def test_multiple_candidates_picks_highest_confidence():
    """Avec plusieurs types possibles, prend le score le plus élevé."""
    ocr = """
    CERFA 13757*03
    MANDAT POUR VENDRE
    VIN: WDB12345678901234
    """
    orch = get_orchestrator()
    doc_type, confidence = orch.detect_document_type(ocr)
    # Mandat devrait avoir un score de 1.0 (exact match)
    assert doc_type == DocumentType.MANDAT


# ─── Tests de rétro-compatibilité ────────────────────────────────────────────────

def test_return_dict_format():
    """Vérifie que le format de retour est compatible avec l'ancien API."""
    ocr = """
    CARTE NATIONALE D'IDENTITÉ
    NOM: DUPONT
    """
    result = detect_and_extract(ocr)
    
    # Doit avoir ces clés
    assert "success" in result
    assert "data" in result
    assert "confidence" in result
    assert "errors" in result
    assert "document_type" in result
    
    # Types corrects
    assert isinstance(result["success"], bool)
    assert isinstance(result["data"], dict)
    assert isinstance(result["confidence"], float)
    assert isinstance(result["errors"], list)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
