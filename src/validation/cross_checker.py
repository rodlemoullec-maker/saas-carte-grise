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


# Documents a scanner pour remplir le CERFA
# - Certificat de cession : immatriculation, VIN, date vente, vendeur/acheteur
# - CNI : identite de l'acheteur
# - Justificatif domicile : adresse de l'acheteur
# Les donnees techniques vehicule viennent de la base types_mines.
DOCUMENTS_OBLIGATOIRES = [
    "certificat_cession",
    "cni",
    "justificatif_domicile",
]


def validate_dossier(
    documents: dict[str, dict],
    genre_vehicule: str = "VP",
    vehicle_found_in_db: bool = True,
    vehicle_data: dict | None = None,
) -> ValidationReport:
    """Valide la cohérence de tous les documents d'un dossier.

    Args:
        documents: Dict avec clé = type de document, valeur = données extraites.
        genre_vehicule: Genre du véhicule (VP, MTL, MTT1, etc.)
        vehicle_found_in_db: True si le véhicule a été trouvé dans la base types mines.
        vehicle_data: Données véhicule issues de la recherche (optionnel).

    Returns:
        ValidationReport avec erreurs, warnings et checks passés.
    """
    report = ValidationReport()

    # 1. Vérifier la présence des documents obligatoires
    _check_documents_presents(documents, genre_vehicule, report)

    # 2. Cohérence noms (acheteur = titulaire CNI)
    _check_noms(documents, report)

    # 3. Validité justificatif de domicile (< 6 mois)
    _check_justificatif_date(documents, report)

    # 4. Validité CNI (non expirée)
    _check_cni_validite(documents, report)

    return report


def _check_documents_presents(docs: dict, genre: str, report: ValidationReport):
    """Vérifie que tous les documents obligatoires sont présents."""
    obligatoires = list(DOCUMENTS_OBLIGATOIRES)

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


def _check_donnees_techniques(
    docs: dict, genre: str, vehicle_found: bool, vehicle_data: dict | None, report: ValidationReport
):
    """Vérifie que les données techniques sont complètes pour le CERFA.

    Si le véhicule n'est pas dans la base, identifie les champs manquants
    et demande les documents complémentaires adaptés au type de véhicule.
    """
    cg = docs.get("carte_grise", {})

    # Champs techniques indispensables pour le CERFA (communs à tous)
    champs_communs = {
        "D1_marque": "Marque",
        "E_vin": "VIN",
        "J1_genre_national": "Genre national",
        "P3_energie": "Énergie",
        "P6_puissance_fiscale": "Puissance fiscale",
    }

    # Champs spécifiques par type de véhicule
    champs_specifiques = {
        "VP": {
            "P1_cylindree": "Cylindrée",
            "P2_puissance_kw": "Puissance kW",
            "S1_nb_places_assises": "Nombre de places",
        },
        "MTL": {
            "P1_cylindree": "Cylindrée",
            "P2_puissance_kw": "Puissance kW",
        },
        "MTT1": {
            "P1_cylindree": "Cylindrée",
            "P2_puissance_kw": "Puissance kW",
        },
        "MTT2": {
            "P1_cylindree": "Cylindrée",
            "P2_puissance_kw": "Puissance kW",
        },
        "REM": {
            "F2_ptac": "PTAC",
            "G1_ptra": "PTRA",
            "F1_masse_max_charge": "Masse maximale en charge",
        },
        "RESP": {
            "F2_ptac": "PTAC",
            "G1_ptra": "PTRA",
            "F1_masse_max_charge": "Masse maximale en charge",
        },
    }

    # Fusionner les champs à vérifier
    champs = dict(champs_communs)
    if genre in champs_specifiques:
        champs.update(champs_specifiques[genre])
    else:
        champs.update(champs_specifiques.get("VP", {}))

    # Si véhicule électrique, la cylindrée n'est pas requise
    energie = cg.get("P3_energie", "")
    if energie and energie.upper() in ("EL", "HY"):
        champs.pop("P1_cylindree", None)

    # Si remorque, énergie et puissance ne sont pas requises
    if genre in ("REM", "RESP"):
        champs.pop("P3_energie", None)
        champs.pop("P6_puissance_fiscale", None)

    # Vérifier chaque champ — d'abord dans la carte grise, puis dans la BDD
    manquants = []
    for champ, label in champs.items():
        val_cg = cg.get(champ)
        val_db = vehicle_data.get(champ) if vehicle_data else None

        if val_cg and str(val_cg).strip() not in ("", "null", "None"):
            continue
        if val_db and str(val_db).strip() not in ("", "null", "None", "0"):
            continue
        manquants.append((champ, label))

    if not manquants and vehicle_found:
        report.add_ok("Données techniques complètes")
        return

    if not manquants and not vehicle_found:
        report.add_ok("Données techniques extraites de la carte grise (véhicule absent de la base)")
        return

    # Il manque des données → déterminer quels documents demander
    labels_manquants = [label for _, label in manquants]

    if vehicle_found:
        report.add_warning(
            f"Données techniques incomplètes sur la carte grise : {', '.join(labels_manquants)}. "
            f"Complétées par la base de données."
        )
        return

    # Véhicule inconnu + données manquantes → demander des documents
    report.add_error(
        f"Véhicule absent de la base de données. "
        f"Données techniques manquantes : {', '.join(labels_manquants)}"
    )

    # Documents à demander selon le type de véhicule
    docs_a_demander = _documents_complementaires(genre, manquants)
    for doc in docs_a_demander:
        report.documents_manquants.append(doc)
        report.add_error(f"Document complémentaire requis : {doc}")


def _documents_complementaires(genre: str, manquants: list[tuple[str, str]]) -> list[str]:
    """Détermine les documents complémentaires à demander selon le véhicule et les données manquantes."""
    docs = []

    # Si données techniques de base manquent
    champs_manquants = {champ for champ, _ in manquants}
    has_missing_tech = champs_manquants & {
        "P1_cylindree", "P2_puissance_kw", "P6_puissance_fiscale",
        "J1_genre_national", "P3_energie",
    }
    has_missing_poids = champs_manquants & {"F2_ptac", "G1_ptra", "F1_masse_max_charge"}

    if genre in ("VP",):
        if has_missing_tech:
            docs.append(
                "Certificat de conformité (COC) ou fiche technique constructeur "
                "— contient : cylindrée, puissance, énergie, genre, places"
            )
    elif genre in ("MTL", "MTT1", "MTT2"):
        if has_missing_tech:
            docs.append(
                "Certificat de conformité moto (COC) ou carte grise lisible "
                "— contient : cylindrée, puissance kW, puissance fiscale, énergie"
            )
        if "P1_cylindree" in champs_manquants:
            docs.append(
                "Préciser la cylindrée exacte du véhicule (nécessaire pour "
                "déterminer le genre MTL/MTT1/MTT2 et la catégorie de permis)"
            )
    elif genre in ("REM", "RESP"):
        if has_missing_poids:
            docs.append(
                "Plaque de tare de la remorque ou certificat de conformité "
                "— contient : PTAC, PTRA, masse maximale en charge"
            )
        if has_missing_tech:
            docs.append(
                "Certificat de conformité remorque (COC) "
                "— contient : genre (REM/RESP), caractéristiques techniques"
            )
    else:
        # Genre inconnu
        if has_missing_tech or has_missing_poids:
            docs.append(
                "Certificat de conformité (COC) du véhicule ou fiche technique "
                "constructeur — le véhicule n'est pas reconnu dans la base de données"
            )

    # Si aucun document spécifique identifié mais données manquantes
    if not docs and manquants:
        labels = [label for _, label in manquants]
        docs.append(
            f"Document complémentaire avec les informations suivantes : {', '.join(labels)}"
        )

    return docs


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
