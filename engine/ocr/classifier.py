"""
Classification automatique des documents uploadés.

Identifie le type de document (CNI, permis, COC, CG, etc.) à partir
du texte OCR brut. Utilise des règles heuristiques + scoring par mots-clés.

Fallback : si la confiance est < 60%, le document reste PENDING
et le pro est invité à préciser le type manuellement.
"""
from __future__ import annotations

from dataclasses import dataclass
from engine.models.documents import DocumentType


@dataclass
class ClassificationResult:
    doc_type: DocumentType
    confidence: float  # 0.0 – 1.0
    matched_keywords: list[str]


# Mots-clés par type de document (pondérés)
_KEYWORDS: dict[DocumentType, list[tuple[str, float]]] = {
    DocumentType.CNI: [
        ("carte nationale d'identite", 1.0),
        ("carte d'identite", 0.9),
        ("republique francaise", 0.4),
        ("nationalite", 0.3),
        ("date de naissance", 0.3),
        ("sexe", 0.2),
        ("nom de naissance", 0.5),
    ],
    DocumentType.PASSEPORT: [
        ("passeport", 1.0),
        ("passport", 0.9),
        ("machine readable", 0.6),
        ("p<fra", 0.8),
        ("type p", 0.5),
    ],
    DocumentType.PERMIS: [
        ("permis de conduire", 1.0),
        ("driving licence", 0.8),
        ("categories", 0.3),
        ("date de delivrance", 0.4),
        ("prefet", 0.4),
    ],
    DocumentType.COC: [
        ("certificat de conformite", 1.0),
        ("certificate of conformity", 0.9),
        ("coc", 0.6),
        ("homologation", 0.5),
        ("type-approval", 0.5),
        ("cnit", 0.5),
        ("puissance nette maximale", 0.6),
        ("masse en charge", 0.4),
    ],
    DocumentType.FACTURE: [
        ("facture", 0.8),
        ("invoice", 0.6),
        ("total ttc", 0.7),
        ("tva", 0.4),
        ("prix unitaire", 0.5),
        ("vehicule neuf", 0.6),
    ],
    DocumentType.ASSURANCE: [
        ("attestation d'assurance", 1.0),
        ("carte verte", 0.8),
        ("memo vehicule assure", 0.9),
        ("responsabilite civile", 0.6),
        ("compagnie d'assurance", 0.5),
        ("police", 0.3),
        ("date d'effet", 0.4),
    ],
    DocumentType.CG_BARREE: [
        ("certificat d'immatriculation", 0.7),
        ("carte grise", 0.6),
        ("vendu le", 0.9),
        ("formule", 0.3),
        ("titulaire", 0.3),
        ("immatriculation", 0.3),
    ],
    DocumentType.CONTROLE_TECHNIQUE: [
        ("controle technique", 1.0),
        ("proces-verbal", 0.5),
        ("resultat", 0.3),
        ("defaut", 0.3),
        ("favorable", 0.4),
        ("contre-visite", 0.5),
        ("centre de controle", 0.5),
    ],
    DocumentType.CERFA_VN: [
        ("cerfa", 0.7),
        ("13749", 0.9),
        ("demande de certificat d'immatriculation", 0.8),
        ("vehicule neuf", 0.5),
    ],
    DocumentType.CERFA_VO: [
        ("cerfa", 0.7),
        ("13750", 0.9),
        ("demande de certificat d'immatriculation", 0.8),
        ("changement de titulaire", 0.6),
    ],
    DocumentType.CERFA_CESSION: [
        ("cerfa", 0.5),
        ("15776", 0.9),
        ("declaration de cession", 0.9),
        ("vendeur", 0.3),
        ("acquereur", 0.4),
    ],
    DocumentType.MANDAT: [
        ("mandat", 0.8),
        ("13757", 0.9),
        ("procuration", 0.7),
        ("mandant", 0.5),
        ("mandataire", 0.5),
    ],
    DocumentType.DA: [
        ("declaration d'achat", 0.9),
        ("13751", 0.9),
        ("achat de vehicule", 0.7),
        ("professionnel acquereur", 0.6),
    ],
    DocumentType.DOMICILE: [
        ("facture", 0.3),
        ("quittance", 0.5),
        ("avis d'imposition", 0.6),
        ("attestation d'hebergement", 0.7),
        ("edf", 0.5),
        ("engie", 0.5),
        ("suez", 0.4),
        ("impot sur le revenu", 0.6),
    ],
    DocumentType.KBIS: [
        ("kbis", 0.9),
        ("extrait du registre", 0.8),
        ("greffe du tribunal", 0.7),
        ("commerce et des societes", 0.6),
        ("avis de situation", 0.5),
        ("sirene", 0.4),
    ],
    DocumentType.TITRE_SEJOUR: [
        ("titre de sejour", 1.0),
        ("carte de sejour", 0.9),
        ("residence", 0.4),
        ("republique francaise", 0.3),
        ("etranger", 0.3),
    ],
    DocumentType.RECEPISEE_DA: [
        ("recepisse", 0.8),
        ("declaration d'achat", 0.7),
        ("enregistrement", 0.4),
    ],
}


class DocumentClassifier:
    """
    Classifie un document à partir de son texte OCR brut.

    Usage :
        result = DocumentClassifier().classify(ocr_text)
        if result.confidence >= 0.60:
            document.type = result.doc_type
            document.auto_classified = True
    """

    def classify(self, ocr_text: str) -> ClassificationResult:
        text_lower = ocr_text.lower()
        # Normaliser les accents de base pour le matching
        text_lower = (
            text_lower
            .replace("é", "e").replace("è", "e").replace("ê", "e").replace("ë", "e")
            .replace("à", "a").replace("â", "a")
            .replace("ù", "u").replace("û", "u")
            .replace("ô", "o").replace("î", "i").replace("ï", "i")
            .replace("ç", "c")
        )

        best_type = DocumentType.CNI
        best_score = 0.0
        best_keywords: list[str] = []

        for doc_type, keywords in _KEYWORDS.items():
            score = 0.0
            matched = []
            for keyword, weight in keywords:
                if keyword in text_lower:
                    score += weight
                    matched.append(keyword)

            # Normaliser par le score max possible pour ce type
            max_possible = sum(w for _, w in keywords)
            if max_possible > 0:
                normalized_score = score / max_possible
            else:
                normalized_score = 0.0

            if normalized_score > best_score:
                best_score = normalized_score
                best_type = doc_type
                best_keywords = matched

        return ClassificationResult(
            doc_type=best_type,
            confidence=min(best_score, 1.0),
            matched_keywords=best_keywords,
        )
