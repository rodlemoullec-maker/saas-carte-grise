"""Gestion de la base stock interne (véhicules en stock de l'entreprise)."""

from datetime import date

from sqlalchemy import create_engine, text

from config.settings import DATABASE_URL

_engine = None


def _get_engine():
    global _engine
    if _engine is None:
        _engine = create_engine(DATABASE_URL)
    return _engine


def add_vehicle(
    vin: str,
    immatriculation: str = "",
    cnit: str = "",
    marque: str = "",
    modele: str = "",
    date_premiere_immat: date | None = None,
    km: int = 0,
    prix_vente: float = 0.0,
) -> int:
    """Ajoute un véhicule au stock.

    Returns:
        ID du véhicule créé.
    """
    engine = _get_engine()
    with engine.connect() as conn:
        result = conn.execute(
            text(
                "INSERT INTO vehicules_stock "
                "(vin, immatriculation, cnit, marque, modele, "
                "date_premiere_immat, km, prix_vente, date_entree) "
                "VALUES (:vin, :immat, :cnit, :marque, :modele, "
                ":date_immat, :km, :prix, CURRENT_DATE) "
                "RETURNING id"
            ),
            {
                "vin": vin,
                "immat": immatriculation,
                "cnit": cnit or None,
                "marque": marque,
                "modele": modele,
                "date_immat": date_premiere_immat,
                "km": km,
                "prix": prix_vente,
            },
        )
        vehicle_id = result.scalar()
        conn.commit()
        return vehicle_id


def search_by_vin(vin: str) -> dict | None:
    """Recherche un véhicule en stock par VIN."""
    engine = _get_engine()
    with engine.connect() as conn:
        result = conn.execute(
            text("SELECT * FROM vehicules_stock WHERE vin = :vin"),
            {"vin": vin.strip().upper()},
        )
        row = result.mappings().fetchone()
        return dict(row) if row else None


def search_by_immatriculation(immat: str) -> dict | None:
    """Recherche un véhicule en stock par immatriculation."""
    engine = _get_engine()
    with engine.connect() as conn:
        result = conn.execute(
            text("SELECT * FROM vehicules_stock WHERE immatriculation = :immat"),
            {"immat": immat.strip().upper()},
        )
        row = result.mappings().fetchone()
        return dict(row) if row else None


def update_status(vehicle_id: int, statut: str) -> None:
    """Met à jour le statut d'un véhicule (en_stock, vendu, reserve, en_cours_cg)."""
    engine = _get_engine()
    with engine.connect() as conn:
        conn.execute(
            text("UPDATE vehicules_stock SET statut = :statut WHERE id = :id"),
            {"statut": statut, "id": vehicle_id},
        )
        if statut == "vendu":
            conn.execute(
                text("UPDATE vehicules_stock SET date_vente = CURRENT_DATE WHERE id = :id"),
                {"id": vehicle_id},
            )
        conn.commit()


def list_stock(statut: str = "en_stock") -> list[dict]:
    """Liste les véhicules en stock par statut."""
    engine = _get_engine()
    with engine.connect() as conn:
        result = conn.execute(
            text("SELECT * FROM vehicules_stock WHERE statut = :statut ORDER BY date_entree DESC"),
            {"statut": statut},
        )
        return [dict(row) for row in result.mappings().fetchall()]
