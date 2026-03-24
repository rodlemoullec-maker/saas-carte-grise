"""
Accès à la base de référence véhicules.

La base est chargée en mémoire au démarrage (fichiers CSV).
En production, migrer vers PostgreSQL (scripts/import_types_mines.py).

Champs disponibles (ADEME voitures neuves) :
  Marque, Libellé modèle, Énergie, Carrosserie, Cylindrée, Gamme,
  Puissance fiscale, Puissance maximale (kW), Poids à vide,
  CO2 vitesse mixte, Bonus-Malus, Prix véhicule

Champs disponibles (motos) :
  Brand, Model, Year, Category, Displacement, Power (hp), Torque,
  Engine cylinder, Fuel system, Dry weight, etc.
"""
from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path

DATA_DIR = Path(__file__).parent.parent.parent / "data" / "types_mines"


@dataclass
class VehicleRecord:
    marque: str
    modele: str
    energie: str
    carrosserie: str | None
    cylindree: int | None
    puissance_fiscale: int | None
    puissance_kw: float | None
    co2_mixte: float | None
    source: str  # "ademe" | "motos_kaggle"


class VehicleDatabase:
    """
    Base de référence véhicules chargée depuis les CSV.

    Utilisée pour :
    1. Vérifier la cohérence des données extraites du COC / facture
    2. Enrichir les champs manquants (puissance fiscale si absente du COC)
    3. Identifier le type de véhicule (VP, moto, etc.)

    TODO: ajouter un index par (marque, modele) pour recherches rapides.
    TODO: migrer vers PostgreSQL pour la production.
    TODO: ajouter les données historiques occasions (ADEME 2012-2015).
    """

    def __init__(self) -> None:
        self._records: list[VehicleRecord] = []
        self._loaded = False

    def load(self) -> None:
        """Charge les CSV en mémoire."""
        self._records = []
        self._load_ademe()
        self._load_motos()
        self._loaded = True

    def _load_ademe(self) -> None:
        path = DATA_DIR / "ademe_car_labelling.csv"
        if not path.exists():
            return
        with open(path, encoding="utf-8-sig") as f:
            reader = csv.DictReader(f, delimiter=";")
            for row in reader:
                try:
                    self._records.append(VehicleRecord(
                        marque=row.get("Marque", "").strip(),
                        modele=row.get("Libellé modèle", "").strip(),
                        energie=row.get("Energie", "").strip(),
                        carrosserie=row.get("Carrosserie", "").strip() or None,
                        cylindree=self._parse_int(row.get("Cylindrée")),
                        puissance_fiscale=self._parse_int(row.get("Puissance fiscale")),
                        puissance_kw=self._parse_float(row.get("Puissance maximale")),
                        co2_mixte=self._parse_float(row.get("CO2 vitesse mixte Min")),
                        source="ademe",
                    ))
                except Exception:
                    continue

    def _load_motos(self) -> None:
        path = DATA_DIR / "motos_kaggle.csv"
        if not path.exists():
            return
        with open(path, encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                try:
                    hp = self._parse_float(row.get("Power (hp)"))
                    kw = round(hp * 0.7457, 1) if hp else None
                    self._records.append(VehicleRecord(
                        marque=row.get("Brand", "").strip(),
                        modele=row.get("Model", "").strip(),
                        energie="essence" if row.get("Fuel system", "").lower() != "electric" else "electrique",
                        carrosserie=None,
                        cylindree=self._parse_int(row.get("Displacement (ccm)")),
                        puissance_fiscale=None,
                        puissance_kw=kw,
                        co2_mixte=None,
                        source="motos_kaggle",
                    ))
                except Exception:
                    continue

    def search(self, marque: str, modele: str | None = None) -> list[VehicleRecord]:
        """Recherche par marque (et modèle optionnel)."""
        if not self._loaded:
            self.load()
        marque_norm = marque.upper().strip()
        results = [r for r in self._records if r.marque.upper() == marque_norm]
        if modele:
            modele_norm = modele.upper().strip()
            results = [r for r in results if modele_norm in r.modele.upper()]
        return results

    def get_stats(self) -> dict:
        if not self._loaded:
            self.load()
        return {
            "total": len(self._records),
            "ademe": sum(1 for r in self._records if r.source == "ademe"),
            "motos": sum(1 for r in self._records if r.source == "motos_kaggle"),
        }

    @staticmethod
    def _parse_int(value: str | None) -> int | None:
        if not value:
            return None
        try:
            return int(str(value).replace(",", ".").split(".")[0])
        except (ValueError, AttributeError):
            return None

    @staticmethod
    def _parse_float(value: str | None) -> float | None:
        if not value:
            return None
        try:
            return float(str(value).replace(",", "."))
        except (ValueError, AttributeError):
            return None


# Instance globale (chargée au démarrage de l'app)
vehicle_db = VehicleDatabase()
