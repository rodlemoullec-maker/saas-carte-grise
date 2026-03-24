"""
Client API BAN — Base Adresse Nationale.

Normalise et géocode les adresses françaises.
API publique, sans clé requise.

Documentation : https://adresse.data.gouv.fr/api-doc/adresse
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass
class BANResult:
    label: str          # Adresse formatée normalisée
    score: float        # Score de confiance (0–1)
    housenumber: str | None
    street: str | None
    postcode: str
    city: str
    context: str | None  # Département, région
    lat: float | None
    lon: float | None
    ban_id: str | None


class BANClient:
    """
    Client pour l'API BAN (Base Adresse Nationale).

    Usage :
    - Normalisation d'adresses avant stockage SIV
    - Vérification qu'une adresse existe réellement
    - Extraction code postal / ville quand OCR est dégradé

    TODO: implémenter les appels HTTP.
    TODO: mettre en cache (TTL : 7 jours pour adresses validées).
    """

    BASE_URL = "https://api-adresse.data.gouv.fr"

    async def search(self, query: str, postcode: str | None = None) -> list[BANResult]:
        """
        Recherche une adresse par texte libre.

        TODO: GET /search/?q={query}&postcode={postcode}&limit=1
        TODO: parser et retourner le meilleur résultat.
        """
        raise NotImplementedError

    async def normalize(self, address: str, city: str, postcode: str) -> BANResult | None:
        """
        Normalise une adresse complète.
        Retourne None si l'adresse n'est pas trouvée avec score > 0.7.

        TODO: construire la requête complète + filtrer par score.
        """
        raise NotImplementedError
