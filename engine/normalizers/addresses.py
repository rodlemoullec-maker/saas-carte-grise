"""
Normalisation des adresses postales.

S'appuie sur l'API BAN (Base Adresse Nationale) pour normaliser
et valider les adresses françaises. L'appel réseau est délégué
à integrations/ban_addresses.py.
"""
from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass
class NormalizedAddress:
    label: str                  # Adresse complète normalisée
    housenumber: str | None
    street: str | None
    postcode: str
    city: str
    score: float                # Score de confiance BAN (0–1)
    ban_id: str | None = None   # Identifiant BAN


def normalize_postcode(cp: str) -> str | None:
    """Normalise un code postal français (5 chiffres)."""
    cp = re.sub(r"\s+", "", cp)
    if re.match(r"^\d{5}$", cp):
        return cp
    # DOM-TOM : 97x, 98x
    if re.match(r"^9[78]\d{3}$", cp):
        return cp
    return None


def addresses_match(addr_a: str, addr_b: str) -> bool:
    """
    Comparaison simplifiée de deux adresses (avant normalisation BAN).
    Utile pour une vérification rapide sans appel réseau.

    TODO: utiliser les coordonnées BAN normalisées pour une comparaison précise.
    """
    def clean(a: str) -> str:
        a = a.lower()
        a = re.sub(r"[,\.\-]", " ", a)
        a = re.sub(r"\s+", " ", a).strip()
        return a

    return clean(addr_a) == clean(addr_b)
