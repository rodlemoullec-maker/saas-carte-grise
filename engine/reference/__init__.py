"""
Base de référence véhicules — utilisée pour enrichir et valider les données extraites.

Sources :
- ademe_car_labelling.csv : voitures neuves (ADEME, données homologation)
- motos_kaggle.csv         : motos 1970-2022 (Kaggle, 576 marques)
- wmi/                     : base WMI constructeurs (NHTSA + EU)

Usage dans le pipeline :
- Vérification cohérence marque/énergie/puissance extraite vs base connue
- Enrichissement des champs manquants (puissance fiscale, PTAC...)
- Identification du type de véhicule depuis le VIN (WMI)
"""
from engine.reference.vehicle_db import VehicleDatabase

__all__ = ["VehicleDatabase"]
