"""
Détection hybride pour rattachement multi-document.

Quand l'agent glisse un nouveau document (ou un email contenant des pièces),
le système cherche un dossier existant qui pourrait correspondre — pour
proposer le rattachement plutôt que de créer systématiquement un nouveau dossier.

Stratégies de match (par ordre de fiabilité décroissante) :
1. Match exact sur VIN (17 caractères) → confiance 1.0
2. Match exact sur immatriculation → confiance 0.95
3. Match exact sur nom client + prénom → confiance 0.85
4. Match fuzzy sur nom client (≥ 90%) → confiance 0.75
5. Match exact sur email client → confiance 0.80
6. Match exact sur téléphone client → confiance 0.80

Le dossier candidat avec le score le plus élevé est retourné, à condition
que le score dépasse un seuil minimum (0.70 par défaut).

L'agent garde toujours le contrôle final : un popup lui propose le rattachement
mais il peut choisir "Créer un nouveau dossier" en un clic.
"""
from __future__ import annotations

import logging
import unicodedata
from dataclasses import dataclass
from datetime import datetime, timedelta

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from api.models.dossier import DossierDB

logger = logging.getLogger(__name__)


# Seuil minimum de confiance pour proposer un rattachement
MATCH_CONFIDENCE_THRESHOLD = 0.70

# Fenêtre de recherche : on ne propose que des dossiers récents (créés < N jours)
# Au-delà, on considère que c'est un nouveau dossier même si le nom matche.
RECENT_DOSSIERS_DAYS = 90


@dataclass
class DossierMatch:
    """Résultat d'un match de dossier."""
    dossier_id: str
    reference: str
    client_nom: str | None
    client_prenom: str | None
    vin: str | None
    immatriculation: str | None
    type: str | None
    status: str
    confidence: float
    match_reason: str  # "vin" | "immatriculation" | "nom_exact" | "nom_fuzzy" | "email" | "telephone"
    created_at: datetime | None


# ─── Normalisation ──────────────────────────────────────────────────────────


def _normalize(s: str | None) -> str:
    """Normalise une chaîne pour comparaison : minuscule, sans accents, espaces collapsed."""
    if not s:
        return ""
    s = unicodedata.normalize("NFKD", s)
    s = "".join(c for c in s if not unicodedata.combining(c))
    return s.lower().strip()


def _normalize_phone(s: str | None) -> str:
    """Normalise un numéro de téléphone : digits uniquement, conversion +33 → 0."""
    if not s:
        return ""
    digits = "".join(c for c in s if c.isdigit())
    if digits.startswith("33") and len(digits) == 11:
        digits = "0" + digits[2:]
    return digits


def _fuzzy_score(a: str, b: str) -> float:
    """
    Score de similarité fuzzy entre deux chaînes (0.0 à 1.0).

    Utilise difflib SequenceMatcher (toujours disponible en stdlib Python).
    Pour de meilleurs résultats, fuzzywuzzy/python-levenshtein peuvent être
    utilisés mais ne sont pas obligatoires.
    """
    if not a or not b:
        return 0.0
    a, b = _normalize(a), _normalize(b)
    if a == b:
        return 1.0
    try:
        from difflib import SequenceMatcher
        return SequenceMatcher(None, a, b).ratio()
    except Exception:
        return 0.0


# ─── Stratégie de match ────────────────────────────────────────────────────


async def find_matching_dossier(
    db: AsyncSession,
    hints: dict,
    *,
    confidence_threshold: float = MATCH_CONFIDENCE_THRESHOLD,
) -> DossierMatch | None:
    """
    Cherche un dossier existant qui correspond aux indices fournis.

    Args:
        db: session SQLAlchemy async
        hints: dict avec les indices extraits :
            - vin (str)
            - immatriculation (str)
            - client_nom (str)
            - client_prenom (str)
            - sender_email / client_email (str)
            - phone / client_telephone (str)
        confidence_threshold: score minimum pour proposer un match

    Returns:
        DossierMatch si un dossier candidat est trouvé, None sinon.
    """
    # Limite temporelle — on ne cherche que dans les dossiers récents
    cutoff = datetime.utcnow() - timedelta(days=RECENT_DOSSIERS_DAYS)

    # Récupérer tous les dossiers récents en cours (PENDING ou DIAGNOSTIC)
    # Les dossiers déjà CERFA_GENERE ou CLOSED ne doivent pas être proposés.
    query = (
        select(DossierDB)
        .where(
            DossierDB.created_at >= cutoff,
            DossierDB.status.in_(["PENDING", "DIAGNOSTIC", "CORRECTION", "ATTENTE_CLIENT"]),
        )
        .order_by(DossierDB.created_at.desc())
    )
    result = await db.execute(query)
    candidates = result.scalars().all()

    if not candidates:
        return None

    best_match: DossierMatch | None = None

    for d in candidates:
        score, reason = _score_dossier(d, hints)
        if score >= confidence_threshold and (best_match is None or score > best_match.confidence):
            best_match = DossierMatch(
                dossier_id=d.id,
                reference=d.reference,
                client_nom=d.client_nom,
                client_prenom=d.client_prenom,
                vin=d.vin,
                immatriculation=d.immatriculation,
                type=d.type,
                status=d.status,
                confidence=score,
                match_reason=reason,
                created_at=d.created_at,
            )

    if best_match:
        logger.info(
            f"[matcher] dossier candidat : {best_match.reference} "
            f"(score={best_match.confidence:.2f}, raison={best_match.match_reason})"
        )

    return best_match


def _score_dossier(dossier: DossierDB, hints: dict) -> tuple[float, str]:
    """
    Calcule le score de match entre un dossier et les indices.

    Retourne (score, raison).
    """
    # 1. VIN exact = quasi certitude
    hint_vin = (hints.get("vin") or "").upper().strip()
    if hint_vin and dossier.vin and hint_vin == dossier.vin.upper().strip():
        return (1.0, "vin")

    # 2. Immatriculation exacte
    hint_immat = _normalize_immat(hints.get("immatriculation"))
    dossier_immat = _normalize_immat(dossier.immatriculation)
    if hint_immat and dossier_immat and hint_immat == dossier_immat:
        return (0.95, "immatriculation")

    # 3. Nom + prénom exacts
    hint_nom = _normalize(hints.get("client_nom"))
    hint_prenom = _normalize(hints.get("client_prenom"))
    d_nom = _normalize(dossier.client_nom)
    d_prenom = _normalize(dossier.client_prenom)
    if hint_nom and d_nom and hint_nom == d_nom:
        if hint_prenom and d_prenom and hint_prenom == d_prenom:
            return (0.85, "nom_exact")
        # Nom seul (sans prénom à comparer)
        if not hint_prenom or not d_prenom:
            return (0.80, "nom_exact")

    # 4. Email exact
    hint_email = _normalize(hints.get("sender_email") or hints.get("client_email"))
    d_email = _normalize(dossier.client_email)
    if hint_email and d_email and hint_email == d_email:
        return (0.80, "email")

    # 5. Téléphone exact
    hint_phone = _normalize_phone(hints.get("phone") or hints.get("client_telephone"))
    d_phone = _normalize_phone(dossier.client_telephone)
    if hint_phone and d_phone and hint_phone == d_phone:
        return (0.80, "telephone")

    # 6. Nom fuzzy (≥ 90% de similarité)
    if hint_nom and d_nom:
        fuzzy = _fuzzy_score(hint_nom, d_nom)
        if fuzzy >= 0.90:
            # On boost si le prénom est aussi similaire
            if hint_prenom and d_prenom:
                fuzzy_p = _fuzzy_score(hint_prenom, d_prenom)
                if fuzzy_p >= 0.90:
                    return (0.78, "nom_fuzzy")
            return (0.75, "nom_fuzzy")

    return (0.0, "none")


def _normalize_immat(immat: str | None) -> str:
    """Normalise une plaque d'immatriculation : majuscule, sans tiret/espace."""
    if not immat:
        return ""
    return immat.upper().replace("-", "").replace(" ", "").strip()


# ─── Helpers pour merger les indices après OCR ─────────────────────────────


def merge_hints(*hint_dicts: dict) -> dict:
    """
    Fusionne plusieurs dicts d'indices en un seul.

    Le dernier indice non-vide gagne. Permet de combiner les indices extraits
    du sujet de l'email + ceux extraits par l'OCR des pièces jointes.
    """
    merged: dict = {}
    for d in hint_dicts:
        if not d:
            continue
        for k, v in d.items():
            if v not in (None, "", [], {}):
                merged[k] = v
    return merged
