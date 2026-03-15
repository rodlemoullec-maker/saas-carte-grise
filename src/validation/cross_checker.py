"""Cross-validation inter-documents.

Vérifie la cohérence entre tous les documents d'un dossier carte grise :
- VIN identique entre carte grise et certificat de cession
- Immatriculation cohérente
- Nom acheteur = nom CNI (fuzzy match)
- Justificatif de domicile < 6 mois
- CNI non expirée
- Contrôle technique valide (si applicable)
- Documents obligatoires présents
"""

from datetime import date, datetime
from dataclasses import dataclass, field


@dataclass
class ValidationReport:
    """Rapport de validation d'un dossier."""
    is_valid: bool = True
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    documents_manquants: list[str] = field(default_factory=list)
    checks_passed: list[str] = field(default_factory=list)

    def add_error(self, msg: str):
        self.errors.append(msg)
        self.is_valid = False

    def add_warning(self, msg: str):
        self.warnings.append(msg)

    def add_ok(self, msg: str):
        self.checks_passed.append(msg)

    def to_dict(self) -> dict:
        return {
            "is_valid": self.is_valid,
            "errors": self.errors,
            "warnings": self.warnings,
            "documents_manquants": self.documents_manquants,
            "checks_passed": self.checks_passed,
            "nb_errors": len(self.errors),
            "nb_warnings": len(self.warnings),
        }


# Documents obligatoires pour un changement de titulaire
DOCUMENTS_OBLIGATOIRES = [
    "carte_grise",
    "certificat_cession",
    "cni",
    "justificatif_domicile",
]

# Genres exemptés de contrôle technique
GENRES_EXEMPTES_CT = ["MTL"]  # Motos < 125cc


def validate_dossier(documents: dict[str, dict], genre_vehicule: str = "VP") -> ValidationReport:
    """Valide la cohérence de tous les documents d'un dossier.

    Args:
        documents: Dict avec clé = type de document, valeur = données extraites.
            Ex: {"carte_grise": {...}, "cni": {...}, "certificat_cession": {...}}
        genre_vehicule: Genre du véhicule (VP, MTL, MTT1, etc.)

    Returns:
        ValidationReport avec erreurs, warnings et checks passés.
    """
    report = ValidationReport()

    # 1. Vérifier la présence des documents obligatoires
    _check_documents_presents(documents, genre_vehicule, report)

    # 2. Cohérence VIN
    _check_vin(documents, report)

    # 3. Cohérence immatriculation
    _check_immatriculation(documents, report)

    # 4. Cohérence noms (acheteur = titulaire CNI)
    _check_noms(documents, report)

    # 5. Validité justificatif de domicile (< 6 mois)
    _check_justificatif_date(documents, report)

    # 6. Validité CNI (non expirée)
    _check_cni_validite(documents, report)

    # 7. Contrôle technique (si applicable)
    _check_controle_technique(documents, genre_vehicule, report)

    return report


def _check_documents_presents(docs: dict, genre: str, report: ValidationReport):
    """Vérifie que tous les documents obligatoires sont présents."""
    obligatoires = list(DOCUMENTS_OBLIGATOIRES)

    # CT obligatoire si pas exempté
    if genre not in GENRES_EXEMPTES_CT:
        obligatoires.append("controle_technique")

    for doc_type in obligatoires:
        if doc_type not in docs or not docs[doc_type]:
            report.documents_manquants.append(doc_type)
            report.add_error(f"Document manquant : {doc_type}")
        else:
            report.add_ok(f"Document présent : {doc_type}")


def _check_vin(docs: dict, report: ValidationReport):
    """Vérifie la cohérence du VIN entre carte grise et cession."""
    cg = docs.get("carte_grise", {})
    cession = docs.get("certificat_cession", {})

    vin_cg = _clean(cg.get("E_vin", ""))
    vin_cession = _clean(cession.get("vin", ""))

    if not vin_cg and not vin_cession:
        report.add_warning("VIN non trouvé dans les documents")
        return

    if vin_cg and vin_cession:
        if vin_cg == vin_cession:
            report.add_ok(f"VIN cohérent : {vin_cg}")
        else:
            report.add_error(f"VIN incohérent : carte grise '{vin_cg}' ≠ cession '{vin_cession}'")
    elif vin_cg:
        report.add_warning("VIN absent du certificat de cession")
    else:
        report.add_warning("VIN absent de la carte grise")


def _check_immatriculation(docs: dict, report: ValidationReport):
    """Vérifie la cohérence de l'immatriculation."""
    cg = docs.get("carte_grise", {})
    cession = docs.get("certificat_cession", {})

    immat_cg = _normalize_immat(cg.get("A_immatriculation", ""))
    immat_cession = _normalize_immat(cession.get("immatriculation", ""))

    if not immat_cg and not immat_cession:
        report.add_warning("Immatriculation non trouvée dans les documents")
        return

    if immat_cg and immat_cession:
        if immat_cg == immat_cession:
            report.add_ok(f"Immatriculation cohérente : {immat_cg}")
        else:
            report.add_error(f"Immatriculation incohérente : CG '{immat_cg}' ≠ cession '{immat_cession}'")


def _check_noms(docs: dict, report: ValidationReport):
    """Vérifie que le nom sur la CNI correspond au nom de l'acheteur."""
    cni = docs.get("cni", {})
    cession = docs.get("certificat_cession", {})

    nom_cni = _clean(cni.get("nom", ""))
    prenom_cni = _clean(cni.get("prenom", ""))
    nom_acheteur = _clean(cession.get("acheteur_nom", ""))
    prenom_acheteur = _clean(cession.get("acheteur_prenom", ""))

    if not nom_cni or not nom_acheteur:
        report.add_warning("Impossible de comparer les noms CNI / cession (données manquantes)")
        return

    # Comparaison fuzzy des noms
    if _fuzzy_match(nom_cni, nom_acheteur):
        report.add_ok(f"Nom cohérent : CNI '{nom_cni}' ≈ cession '{nom_acheteur}'")
    else:
        report.add_error(f"Nom incohérent : CNI '{nom_cni}' ≠ cession '{nom_acheteur}'")

    # Comparaison prénoms (warning seulement)
    if prenom_cni and prenom_acheteur:
        if _fuzzy_match(prenom_cni, prenom_acheteur):
            report.add_ok(f"Prénom cohérent : '{prenom_cni}' ≈ '{prenom_acheteur}'")
        else:
            report.add_warning(f"Prénom potentiellement différent : CNI '{prenom_cni}' ≠ cession '{prenom_acheteur}'")


def _check_justificatif_date(docs: dict, report: ValidationReport):
    """Vérifie que le justificatif de domicile a moins de 6 mois."""
    justif = docs.get("justificatif_domicile", {})
    date_str = justif.get("date_document", "")

    if not date_str:
        report.add_warning("Date du justificatif de domicile non trouvée")
        return

    date_doc = _parse_date(date_str)
    if not date_doc:
        report.add_warning(f"Date du justificatif non parsable : '{date_str}'")
        return

    age_jours = (date.today() - date_doc).days
    if age_jours <= 180:
        report.add_ok(f"Justificatif récent : {age_jours} jours (max 180)")
    else:
        report.add_error(f"Justificatif trop ancien : {age_jours} jours (max 180)")


def _check_cni_validite(docs: dict, report: ValidationReport):
    """Vérifie que la CNI n'est pas expirée."""
    cni = docs.get("cni", {})
    date_str = cni.get("date_validite", "")

    if not date_str:
        report.add_warning("Date de validité CNI non trouvée")
        return

    date_val = _parse_date(date_str)
    if not date_val:
        report.add_warning(f"Date de validité CNI non parsable : '{date_str}'")
        return

    if date_val >= date.today():
        report.add_ok(f"CNI valide jusqu'au {date_val}")
    else:
        report.add_error(f"CNI expirée depuis le {date_val}")


def _check_controle_technique(docs: dict, genre: str, report: ValidationReport):
    """Vérifie le contrôle technique (si applicable)."""
    if genre in GENRES_EXEMPTES_CT:
        report.add_ok(f"CT non requis pour genre {genre}")
        return

    ct = docs.get("controle_technique", {})
    if not ct:
        return  # Déjà signalé comme document manquant

    # Vérifier le résultat
    resultat = _clean(ct.get("resultat", ""))
    if "favorable" in resultat.lower() and "defavorable" not in resultat.lower():
        report.add_ok(f"CT favorable")
    elif resultat:
        report.add_error(f"CT non favorable : {resultat}")
    else:
        report.add_warning("Résultat du CT non trouvé")

    # Vérifier la date de validité
    date_str = ct.get("date_limite_validite", "")
    if date_str:
        date_val = _parse_date(date_str)
        if date_val:
            if date_val >= date.today():
                report.add_ok(f"CT valide jusqu'au {date_val}")
            else:
                report.add_error(f"CT expiré depuis le {date_val}")


# --- Utilitaires ---

def _clean(value: str | None) -> str:
    """Nettoie une chaîne : strip, uppercase."""
    if not value:
        return ""
    return str(value).strip().upper()


def _normalize_immat(immat: str) -> str:
    """Normalise une immatriculation (retire tirets, espaces)."""
    return _clean(immat).replace("-", "").replace(" ", "")


def _fuzzy_match(a: str, b: str, threshold: float = 0.8) -> bool:
    """Comparaison floue de deux chaînes.

    Utilise la distance de Levenshtein simplifiée.
    Retourne True si la similarité est >= threshold.
    """
    a, b = a.upper(), b.upper()
    if a == b:
        return True

    # Vérifier si l'un contient l'autre
    if a in b or b in a:
        return True

    # Distance de Levenshtein
    len_a, len_b = len(a), len(b)
    if len_a == 0 or len_b == 0:
        return False

    matrix = [[0] * (len_b + 1) for _ in range(len_a + 1)]
    for i in range(len_a + 1):
        matrix[i][0] = i
    for j in range(len_b + 1):
        matrix[0][j] = j

    for i in range(1, len_a + 1):
        for j in range(1, len_b + 1):
            cost = 0 if a[i - 1] == b[j - 1] else 1
            matrix[i][j] = min(
                matrix[i - 1][j] + 1,
                matrix[i][j - 1] + 1,
                matrix[i - 1][j - 1] + cost,
            )

    distance = matrix[len_a][len_b]
    max_len = max(len_a, len_b)
    similarity = 1 - (distance / max_len)
    return similarity >= threshold


def _parse_date(date_str: str) -> date | None:
    """Parse une date en plusieurs formats courants."""
    formats = [
        "%d/%m/%Y",  # 15/03/2026
        "%d-%m-%Y",  # 15-03-2026
        "%Y-%m-%d",  # 2026-03-15
        "%d.%m.%Y",  # 15.03.2026
        "%d %m %Y",  # 15 03 2026
    ]
    date_str = date_str.strip()
    for fmt in formats:
        try:
            return datetime.strptime(date_str, fmt).date()
        except ValueError:
            continue
    return None
