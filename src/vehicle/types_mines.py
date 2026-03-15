"""Requêtes base types mines (CNIT → caractéristiques techniques).

Interroge la table PostgreSQL types_mines pour obtenir la fiche
technique d'un véhicule à partir de son CNIT.
"""

from sqlalchemy import create_engine, text

from config.settings import DATABASE_URL

_engine = None


def _get_engine():
    global _engine
    if _engine is None:
        _engine = create_engine(DATABASE_URL)
    return _engine


def search_by_cnit(cnit: str) -> dict | None:
    """Recherche un véhicule par CNIT exact.

    Args:
        cnit: Code National d'Identification du Type.

    Returns:
        Dict avec les caractéristiques techniques ou None.
    """
    engine = _get_engine()
    with engine.connect() as conn:
        result = conn.execute(
            text("SELECT * FROM types_mines WHERE cnit = :cnit"),
            {"cnit": cnit.strip()},
        )
        row = result.mappings().fetchone()
        if row:
            return dict(row)
    return None


def search_by_marque_modele(marque: str, modele: str = "") -> list[dict]:
    """Recherche des véhicules par marque et optionnellement modèle.

    Args:
        marque: Nom de la marque (recherche partielle).
        modele: Nom du modèle ou dénomination (optionnel).

    Returns:
        Liste de dicts avec les caractéristiques techniques.
    """
    engine = _get_engine()
    with engine.connect() as conn:
        if modele:
            result = conn.execute(
                text(
                    "SELECT * FROM types_mines "
                    "WHERE UPPER(marque) LIKE UPPER(:marque) "
                    "AND UPPER(denomination_commerciale) LIKE UPPER(:modele) "
                    "LIMIT 50"
                ),
                {"marque": f"%{marque.strip()}%", "modele": f"%{modele.strip()}%"},
            )
        else:
            result = conn.execute(
                text(
                    "SELECT * FROM types_mines "
                    "WHERE UPPER(marque) LIKE UPPER(:marque) "
                    "LIMIT 50"
                ),
                {"marque": f"%{marque.strip()}%"},
            )
        return [dict(row) for row in result.mappings().fetchall()]


def search_by_tvv(tvv: str) -> dict | None:
    """Recherche un véhicule par TVV (Type Variante Version).

    Le TVV est souvent dans le champ D.2 de la carte grise.
    Il peut correspondre au CNIT ou en être une partie.

    Args:
        tvv: Code TVV.

    Returns:
        Dict ou None.
    """
    engine = _get_engine()
    with engine.connect() as conn:
        # Recherche exacte d'abord
        result = conn.execute(
            text("SELECT * FROM types_mines WHERE cnit = :tvv"),
            {"tvv": tvv.strip()},
        )
        row = result.mappings().fetchone()
        if row:
            return dict(row)

        # Recherche partielle (le CNIT peut contenir le TVV)
        result = conn.execute(
            text("SELECT * FROM types_mines WHERE cnit LIKE :tvv LIMIT 10"),
            {"tvv": f"%{tvv.strip()}%"},
        )
        row = result.mappings().fetchone()
        if row:
            return dict(row)

    return None


def search_fuzzy(marque: str, energie: str = "", cylindree: int = 0) -> list[dict]:
    """Recherche floue pour trouver un véhicule proche.

    Utile quand le CNIT exact n'est pas trouvé.

    Args:
        marque: Marque du véhicule.
        energie: Code énergie (ES, GO, EL, etc.).
        cylindree: Cylindrée en cm³.

    Returns:
        Liste de résultats possibles.
    """
    engine = _get_engine()
    conditions = ["UPPER(marque) LIKE UPPER(:marque)"]
    params = {"marque": f"%{marque.strip()}%"}

    if energie:
        conditions.append("energie = :energie")
        params["energie"] = energie.strip().upper()

    if cylindree > 0:
        # Tolérance de ±50 cm³
        conditions.append("cylindree BETWEEN :cyl_min AND :cyl_max")
        params["cyl_min"] = cylindree - 50
        params["cyl_max"] = cylindree + 50

    where = " AND ".join(conditions)
    query = f"SELECT * FROM types_mines WHERE {where} LIMIT 20"

    with engine.connect() as conn:
        result = conn.execute(text(query), params)
        return [dict(row) for row in result.mappings().fetchall()]
