"""
Client API NHTSA vPIC — décodage VIN et lookup WMI.

Permet de vérifier la cohérence entre le WMI (3 premiers caractères du VIN)
et le constructeur déclaré dans le COC.

API publique, sans clé requise.
Documentation : https://vpic.nhtsa.dot.gov/api/
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass
class VINDecodeResult:
    vin: str
    make: str | None            # Marque
    manufacturer: str | None    # Constructeur (nom complet)
    model: str | None
    model_year: str | None
    vehicle_type: str | None    # PASSENGER CAR, MOTORCYCLE, etc.
    plant_country: str | None   # Pays de fabrication
    wmi: str
    error_code: str | None


class NHTSAClient:
    """
    Client pour l'API NHTSA vPIC.

    Usage principal :
    - Lookup WMI → identifier le constructeur depuis les 3 premiers chars du VIN
    - Détection de fraude si WMI ≠ constructeur déclaré dans COC
    - Informations complémentaires sur le véhicule

    Note : la base NHTSA est principalement nord-américaine.
    Pour les VIN européens, certains WMI peuvent être absents.
    TODO: enrichir avec base OICA / base EU constructeurs.
    """

    BASE_URL = "https://vpic.nhtsa.dot.gov/api/vehicles"

    async def decode_vin(self, vin: str) -> VINDecodeResult | None:
        """
        Décode un VIN complet.

        TODO: GET /DecodeVinValues/{vin}?format=json
        TODO: parser la réponse Results[0].
        TODO: gérer VIN Europe non trouvés (code erreur 6 NHTSA).
        """
        raise NotImplementedError

    async def lookup_wmi(self, wmi: str) -> str | None:
        """
        Retourne le fabricant correspondant à un WMI (3 chars).

        TODO: GET /DecodeWMI/{wmi}?format=json
        TODO: retourner le champ Manufacturer.
        TODO: mettre en cache (base stable, TTL : 30 jours).
        """
        raise NotImplementedError
