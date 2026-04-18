"""
Patterns regex optimisés pour OCR français — Gestion des variations réelles.

Patterns robustes pour:
- Variations de casse (majuscule/minuscule)
- Espaces et séparateurs variables
- Accents mal reconnus par OCR
- Formats alternatifs courants
- Labels variés
"""
from __future__ import annotations

import re
from typing import Optional

# ──────────────────────────────────────────────────────────────────────────
# Patterns Optimisés — Robustes aux variations OCR
# ──────────────────────────────────────────────────────────────────────────

class OptimizedPatterns:
    """Patterns regex robustes testés contre données réelles OCR."""

    # ─── VIN (Vehicle Identification Number) ────────────────────────────
    # Accepte: "VIN:", "v.i.n.:", "V.I.N.:", "Numéro VIN:", espaces intra-VIN
    # {16,17} + 1 terminal = 17-18 chars total
    VIN = r"(?:v\.?i\.?n\.?|vin|n[uú]m[e]?ro\s+vin)\s*[:\s]+((?:[A-HJ-NPR-Z0-9][ ]?){16,17}[A-HJ-NPR-Z0-9])"
    
    # Fallback sans label — espace max 1 (pas de saut de ligne)
    VIN_ALT = r"(?<![A-HJ-NPR-Z0-9])((?:[A-HJ-NPR-Z0-9][ ]?){16,17}[A-HJ-NPR-Z0-9])(?![A-HJ-NPR-Z0-9])"

    # ─── Immatriculation (SIV moderne: AB-123-CD) ────────────────────────
    # Accepte: avec/sans espaces, tirets, labels optionnels, casse variable
    IMMAT = r"(?:immatriculation|immat[a-z]*|n[°º]\s*(?:immat|plate)|plate\s*number)?\s*[:\s]*([A-Z]{2}[\s\-]?\d{3}[\s\-]?[A-Z]{2})(?=\s|$|[^A-Z0-9])"

    # ─── Date (JJ/MM/AAAA, JJ.MM.AAAA, JJ-MM-AAAA, JJ MM AAAA) ──────────
    # Accepte: 1-2 digits jour/mois, 4 ou 2 digits année, variantes séparateurs
    DATE = r"(\d{1,2}[.\/\-\s]\d{1,2}[.\/\-\s](?:\d{4}|\d{2}))"

    # ─── SIREN (Système d'Identification du Répertoire des Entreprises) ──
    # Format: 9 chiffres, avec/sans espaces/tirets, avec label optionnel
    SIREN = r"(?:s\.?i\.?r\.?e\.?n\.?|siren)?\s*[:\s]*([0-9]{3}[\s\-]?[0-9]{3}[\s\-]?[0-9]{3}|[0-9]{9})(?!\d)"

    # ─── SIRET (Numéro d'établissement) ─────────────────────────────────
    # Format: 14 chiffres (9 SIREN + 5 établissement), avec/sans espaces
    SIRET = r"(?:s\.?i\.?r\.?e\.?t\.?|siret|n[°º]\s*siret)?\s*[:\s]*([0-9]{3}\s?[0-9]{3}\s?[0-9]{3}\s?[0-9]{5}|[0-9]{14})(?!\d)"

    # ─── Noms (Robuste aux accents mal reconnus) ──────────────────────────
    # Accepte: majuscule, minuscule, accents, tirets, espaces multiples
    NAME = r"(?:nom|name|surname)[\/\s]*(?:\([^)]*\))?[:\s]*([A-ZÀ-Ü][A-ZÀ-Üa-zà-ü\'\-\s]{1,50})"

    # ─── Prénom (Similar to NAME) ──────────────────────────────────────
    PRENOM = r"(?:pr[eé]nom|given\s+name)[\/\s]*(?:\([^)]*\))?[:\s]*([A-ZÀ-Üa-zà-ü,\'\-\s]{2,60})"

    # ─── Signatures (Rejet explicite vs acceptée) ─────────────────────────
    # REJET: [MISSING], [BLANK], [NON SIGNÉE]
    SIGNATURE_REJECT = r"\[(MISSING|BLANK|NON\s+SIGN[ÉE]{1,2}|NOT\s+SIGNED)\]"
    
    # ACCEPTÉE: [signature], [SIGNÉE], "Signé le", etc.
    SIGNATURE_ACCEPT = r"\[s(?:ignature|ign[eé]e?|igned)\]|(?:sign[eé]e?|signed).{0,30}(?:present|date|le\s+\d)"

    # ─── CNIT (Certificat d'immatriculation) ────────────────────────────
    # Format: GB-AB-123-45-A-456-789 ou variantes
    CNIT = r"(?:cnit|n[°º]\s*cnit)?\s*[:\s]*([A-Z]{2}[\s\-][A-Z]{2}[\s\-]\d{3}[\s\-]\d{2}[\s\-][A-Z][\s\-]\d{3}[\s\-]\d{3})"

    # ─── Numéro de document (CNI: 12 digits, Passeport: 2L+7D) ──────────
    DOC_NUMBER_CNI = r"(?:n[°º]?|num[e]?ro)?\s*[:\s]*(\d{12})"
    DOC_NUMBER_PASSPORT = r"(?:n[°º]?|num[e]?ro)?\s*[:\s]*(\d{2}[A-Z]{2}\d{5})"

    # ─── Montants (Prix HT/TTC, montants génériques) ────────────────────
    # Accepte: avec/sans espaces milliers, points/virgules décimales
    AMOUNT = r"([0-9]{1,3}(?:\s[0-9]{3}|[0-9]{3})*(?:[.,][0-9]{1,2})?)\s*(?:€|euros?)"

    # ─── Email ───────────────────────────────────────────────────────────
    EMAIL = r"([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})"

    # ─── Téléphone français ──────────────────────────────────────────────
    PHONE_FR = r"(?:0|\+33)[1-9](?:[0-9]{8}|\s?[0-9](?:\s?[0-9]){7})"


class OptimizedExtraction:
    """Fonctions d'extraction robustes avec gestion d'erreurs."""

    @staticmethod
    def extract_vin(text: str) -> Optional[str]:
        """Extrait VIN de manière robuste."""
        # Essaie d'abord le pattern avec label (VIN:, v.i.n., etc.)
        m = re.search(OptimizedPatterns.VIN, text, re.IGNORECASE)
        if m:
            vin = m.group(1).replace(' ', '')  # Enlève espaces
            if len(vin) in [17, 18]:
                return vin
        
        # Fallback: essaie pattern alternatif (VIN standalone)
        m = re.search(OptimizedPatterns.VIN_ALT, text, re.IGNORECASE)
        if m:
            vin = m.group(1).replace(' ', '')  # Enlève espaces
            if len(vin) in [17, 18]:
                return vin
        
        # Dernier recours: cherche directement une séquence 17-18 alphanum valides
        m = re.search(r"(?<![A-HJ-NPR-Z0-9])([A-HJ-NPR-Z0-9]{17,18})(?![A-HJ-NPR-Z0-9])", text)
        if m:
            return m.group(1)
        
        return None

    @staticmethod
    def extract_immatriculation(text: str) -> Optional[str]:
        """Extrait immatriculation de manière robuste."""
        m = re.search(OptimizedPatterns.IMMAT, text, re.IGNORECASE)
        if m:
            # Normalise: ajoute tirets au format standard
            immat = m.group(1).upper()
            # Nettoie espaces/tirets
            immat_clean = immat.replace(' ', '').replace('-', '')
            # Reformate: AB123CD → AB-123-CD
            if len(immat_clean) == 7 and immat_clean[:2].isalpha() and immat_clean[2:5].isdigit() and immat_clean[5:].isalpha():
                return f"{immat_clean[:2]}-{immat_clean[2:5]}-{immat_clean[5:]}"
            return immat
        return None

    @staticmethod
    def extract_date(text: str, strict: bool = False) -> Optional[str]:
        """Extrait date et la normalise en ISO 8601."""
        m = re.search(OptimizedPatterns.DATE, text, re.IGNORECASE)
        if not m:
            return None
        
        date_str = m.group(1).replace(' ', '/')
        
        # Essaie les formats courants
        import datetime
        for fmt in ("%d/%m/%Y", "%d/%m/%y", "%d.%m.%Y", "%d.%m.%y", "%d-%m-%Y", "%d-%m-%y"):
            try:
                d = datetime.datetime.strptime(date_str, fmt)
                # Si année > 2050, probablement année 2-digit (ex: 88 → 1988)
                if d.year > 2050:
                    d = d.replace(year=d.year - 100)
                return d.strftime("%Y-%m-%d")
            except ValueError:
                continue
        
        return None if strict else date_str

    @staticmethod
    def extract_siren(text: str) -> Optional[str]:
        """Extrait SIREN et le normalise."""
        m = re.search(OptimizedPatterns.SIREN, text, re.IGNORECASE)
        if m:
            siren = m.group(1).replace(' ', '').replace('-', '')
            # Valide: 9 chiffres
            if len(siren) == 9 and siren.isdigit():
                return siren
        return None

    @staticmethod
    def extract_siret(text: str) -> Optional[str]:
        """Extrait SIRET et le normalise."""
        m = re.search(OptimizedPatterns.SIRET, text, re.IGNORECASE)
        if m:
            siret = m.group(1).replace(' ', '').replace('-', '')
            # Valide: 14 chiffres
            if len(siret) == 14 and siret.isdigit():
                return siret
        return None

    @staticmethod
    def extract_name(text: str) -> Optional[str]:
        """Extrait nom de manière robuste."""
        m = re.search(OptimizedPatterns.NAME, text, re.IGNORECASE)
        if m:
            name = m.group(1).strip()
            # Enlève espaces multiples, normalise casse
            name = ' '.join(name.split()).upper()
            return name
        return None

    @staticmethod
    def is_signature_present(text: str) -> Optional[bool]:
        """Détecte si signature présente (True/False/None = indéterminé)."""
        if re.search(OptimizedPatterns.SIGNATURE_REJECT, text, re.IGNORECASE):
            return False
        if re.search(OptimizedPatterns.SIGNATURE_ACCEPT, text, re.IGNORECASE):
            return True
        return None

    @staticmethod
    def extract_amount(text: str) -> Optional[float]:
        """Extrait montant et le convertit en float."""
        m = re.search(OptimizedPatterns.AMOUNT, text, re.IGNORECASE)
        if m:
            amount_str = m.group(1).replace(' ', '').replace(',', '.')
            try:
                return float(amount_str)
            except ValueError:
                pass
        return None


# ──────────────────────────────────────────────────────────────────────────
# Tests de validation
# ──────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    # Test VIN
    test_vins = [
        "VIN: WDB12345678901234",
        "v.i.n.: WDB12345678901234",
        "VIN WDB12345678901234",
        "numéro vin: WDB12345678901234",
    ]
    print("VIN Tests:")
    for test in test_vins:
        result = OptimizedExtraction.extract_vin(test)
        print(f"  {test[:30]:30} → {result or 'FAILED'}")
    
    # Test Immatriculation
    test_immats = [
        "AB-123-CD",
        "immatriculation: AB 123 CD",
        "immat AB-123-CD",
        "(AB-123-CD)",
    ]
    print("\nImmatriculation Tests:")
    for test in test_immats:
        result = OptimizedExtraction.extract_immatriculation(test)
        print(f"  {test[:30]:30} → {result or 'FAILED'}")
    
    # Test Date
    test_dates = [
        "15/04/2026",
        "15.04.2026",
        "15-04-26",
        "15 04 2026",
    ]
    print("\nDate Tests:")
    for test in test_dates:
        result = OptimizedExtraction.extract_date(test)
        print(f"  {test[:30]:30} → {result or 'FAILED'}")
    
    # Test Signature
    test_sigs = [
        "[SIGNÉE]",
        "[MISSING]",
        "Signé le 15/04/2026",
        "[NON SIGNÉE]",
    ]
    print("\nSignature Tests:")
    for test in test_sigs:
        result = OptimizedExtraction.is_signature_present(test)
        status = {True: "✓ Présente", False: "✗ Absente", None: "? Indéterminé"}
        print(f"  {test[:30]:30} → {status[result]}")
