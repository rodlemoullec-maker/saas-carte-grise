"""
Client API INSEE Sirene — validation SIRET.

Vérifie qu'un SIRET est actif et correspond bien
à un professionnel de l'automobile (code NAF).

Codes NAF automobile :
- 4511Z : Commerce de voitures et véhicules légers
- 4519Z : Commerce d'autres véhicules automobiles
- 4540Z : Commerce et réparation de motocycles
- 4520A : Entretien et réparation de véhicules légers
- 4531Z : Commerce de gros d'équipements automobiles
- 4532Z : Commerce de détail d'équipements automobiles
"""
from __future__ import annotations

from dataclasses import dataclass

import httpx

NAF_CODES_AUTOMOBILE = {
    "4511Z", "4519Z", "4540Z", "4520A", "4520B",
    "4531Z", "4532Z", "4541Z", "4542Z",
}


@dataclass
class SIRETInfo:
    siret: str
    siren: str
    nom_entreprise: str
    denomination: str | None
    naf_code: str
    naf_libelle: str
    etat_administratif: str       # A = actif, F = fermé
    date_creation: str | None
    adresse: str | None
    est_automobile: bool


class INSEESireneClient:
    """
    Client pour l'API Sirene de l'INSEE.
    Documentation : https://api.insee.fr/catalogue/site/themes/wso2/subthemes/insee/pages/item-info.jag?name=Sirene&version=V3.11&provider=insee

    TODO: implémenter l'authentification OAuth2 (clé INSEE requise)
    TODO: gérer le rate limiting (max 30 req/min en version gratuite)
    TODO: mettre en cache les réponses (TTL : 24h)
    """

    def __init__(self, api_key: str, base_url: str = "https://api.insee.fr/entreprises/sirene/V3.11") -> None:
        self.api_key = api_key
        self.base_url = base_url

    async def get_etablissement(self, siret: str) -> SIRETInfo | None:
        """
        Récupère les informations d'un établissement par SIRET.

        TODO: implémenter l'appel HTTP.
        TODO: parser la réponse JSON.
        TODO: gérer les erreurs 404 (SIRET inconnu), 429 (rate limit).
        """
        raise NotImplementedError

    async def is_active_automobile_professional(self, siret: str) -> tuple[bool, str]:
        """
        Vérifie si le SIRET correspond à un professionnel automobile actif.

        Retourne (is_valid, reason_if_not).

        TODO: implémenter en s'appuyant sur get_etablissement().
        """
        raise NotImplementedError
