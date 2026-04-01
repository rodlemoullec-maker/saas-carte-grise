"""
Validateur réglementaire — permis, puissance véhicule, âge, ancienneté.

Détermine dynamiquement les documents requis côté client en fonction :
- Du type de véhicule (moto/voiture, catégorie L, puissance kW)
- Du permis déposé par le client (catégories, dates)
- De l'âge du client (extrait de la CNI)
- De l'ancienneté du permis B (pour la formation 7h)

Migré depuis demo_server.py — fonctions :
_get_vehicle_power_info, _determine_permis_requis, _check_anciennete_permis_b,
_get_client_age
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Any


# ─── Catégories véhicule L (deux/trois-roues) ────────────────────────────────
#
# | Catégorie  | Puissance max   | Permis requis | Alternative permis B         |
# |------------|-----------------|---------------|------------------------------|
# | L1e        | ≤ 4 kW          | AM (ou BSR)   | B suffit (AM inclus)         |
# | L3e-A1     | ≤ 11 kW         | A1            | B + formation 7h (B ≥ 2 ans) |
# | L3e-A2     | ≤ 35 kW         | A2            | Non                          |
# | L3e-A3     | > 35 kW         | A             | Non — 2 ans A2 + formation   |
# | L5e        | ≤ 15 kW         | A1            | B + formation 7h (B ≥ 2 ans) |
# | L5e        | > 15 kW         | A             | B + formation 7h (≥ 21 ans)  |
# | Électrique | Mêmes seuils kW | Idem          |                              |


@dataclass
class VehicleInfo:
    categorie_j: str | None = None
    puissance_kw: float | None = None
    cylindree_cc: float | None = None
    genre_national: str | None = None
    is_moto: bool = False
    is_electrique: bool = False
    debridable: bool = False
    debridable_vers: list[str] = field(default_factory=list)


@dataclass
class PermisRequis:
    permis_min: str  # AM, A1, A2, A, B
    formation_7h: bool = False
    age_min: int | None = None
    age_min_formation: int | None = None
    tricycle_puissant: bool = False
    debridable: bool = False
    puissance_inconnue: bool = False
    message: str | None = None


@dataclass
class AncienneteResult:
    eligible_formation_7h: bool = False
    exempt_formation: bool = False
    attestation_invalide: bool = False
    anciennete_inconnue: bool = False
    date_obtention_b: str | None = None
    date_eligible: str | None = None
    anciennete_annees: int | None = None
    anciennete_mois: int | None = None
    message: str = ""
    action: str | None = None


def get_vehicle_power_info(documents_vendeur: list[dict[str, Any]]) -> VehicleInfo:
    """Extrait les infos de puissance du véhicule depuis les docs vendeur."""
    info = VehicleInfo()

    for d in documents_vendeur:
        ext = d.get("extracted_data", {})
        if not ext:
            continue

        cat_j = ext.get("categorie_j", "")
        if cat_j and cat_j.upper().startswith("L"):
            info.categorie_j = cat_j.upper()
            info.is_moto = True

        genre = ext.get("genre_national", "")
        if genre and genre.upper() in ("MTL", "MTT1", "MTT2", "CL", "QM", "CYCL"):
            info.genre_national = genre.upper()
            info.is_moto = True

        p_kw = ext.get("puissance_nette_p2") or ext.get("puissance_kw")
        if p_kw:
            try:
                info.puissance_kw = float(p_kw)
            except (ValueError, TypeError):
                pass

        cyl = ext.get("cylindree_p1") or ext.get("cylindree")
        if cyl:
            try:
                info.cylindree_cc = float(cyl)
            except (ValueError, TypeError):
                pass

        energie = (ext.get("energie") or "").upper()
        if energie in ("ELECTRIQUE", "ELECTRIC", "EL", "ELEC"):
            info.is_electrique = True

        if ext.get("debridable"):
            info.debridable = True
            info.debridable_vers = ext.get("debridable_vers", [])

    return info


def determine_permis_requis(vehicle_info: VehicleInfo) -> PermisRequis:
    """Détermine le permis minimum requis pour un véhicule."""
    if not vehicle_info.is_moto:
        return PermisRequis(permis_min="B", message=None)

    puissance = vehicle_info.puissance_kw
    cylindree = vehicle_info.cylindree_cc
    cat_j = vehicle_info.categorie_j or ""

    # Débridable → permis A ou A2 requis
    if vehicle_info.debridable and ("A2" in vehicle_info.debridable_vers or "A3" in vehicle_info.debridable_vers):
        max_cat = "A" if "A3" in vehicle_info.debridable_vers else "A2"
        return PermisRequis(
            permis_min=max_cat, debridable=True,
            message=(
                f"Véhicule {cat_j} homologué en version bridée mais le COC indique "
                f"une conversion possible vers {'/'.join(vehicle_info.debridable_vers)}. "
                f"Un permis {max_cat} est requis."
            ),
        )

    # Cyclomoteur (L1e) — ≤ 4 kW
    if cat_j.startswith("L1") or (puissance is not None and puissance <= 4):
        return PermisRequis(
            permis_min="AM",
            message="Cyclomoteur (≤ 4 kW) — permis AM, B ou supérieur suffit.",
        )

    is_tricycle = cat_j.startswith("L5")

    # Moto légère L3e ≤ 11 kW
    if not is_tricycle and puissance is not None and puissance <= 11:
        return PermisRequis(
            permis_min="A1", formation_7h=True, age_min_formation=20,
            message=f"Véhicule {cat_j} de {puissance} kW — permis A1 requis, ou permis B + formation 7h.",
        )

    # Tricycle L5e ≤ 15 kW
    if is_tricycle and puissance is not None and puissance <= 15:
        return PermisRequis(
            permis_min="A1", formation_7h=True, age_min_formation=20,
            message=f"Tricycle {cat_j} de {puissance} kW — permis A1 ou B + formation 7h.",
        )

    # Tricycle L5e > 15 kW — B + formation possible si ≥ 21 ans
    if is_tricycle and puissance is not None and puissance > 15:
        return PermisRequis(
            permis_min="A", formation_7h=True, age_min_formation=21, tricycle_puissant=True,
            message=f"Tricycle {cat_j} de {puissance} kW — permis A requis, ou B + formation 7h (âge ≥ 21 ans).",
        )

    # Cylindrée ≤ 125cc sans puissance connue
    if cylindree is not None and cylindree <= 125 and puissance is None:
        return PermisRequis(
            permis_min="A1", formation_7h=True,
            message="Véhicule 125 cc — permis A1 ou B + formation 7h.",
        )

    # Moto intermédiaire ≤ 35 kW
    if puissance is not None and puissance <= 35:
        return PermisRequis(
            permis_min="A2", age_min=18,
            message=f"Véhicule {cat_j} de {puissance} kW — permis A2 requis (min 18 ans).",
        )

    # Moto puissante > 35 kW
    if puissance is not None and puissance > 35:
        return PermisRequis(
            permis_min="A", age_min=20,
            message=f"Véhicule {cat_j} de {puissance} kW — permis A requis (min 20 ans, ou 24 en accès direct).",
        )

    # Puissance inconnue → sécurité
    return PermisRequis(
        permis_min="A2", puissance_inconnue=True,
        message="Deux-roues motorisé détecté mais puissance non extraite. Permis moto requis par sécurité.",
    )


def check_anciennete_permis_b(
    date_obtention_b: date | None,
    date_attestation: date | None = None,
) -> AncienneteResult:
    """
    Vérifie l'ancienneté du permis B pour la formation 7h.

    Logique en deux temps :
    1. Si attestation fournie → date_B + 2 ans ≤ date_attestation
    2. Sinon → date_B + 2 ans ≤ aujourd'hui
    """
    if not date_obtention_b:
        return AncienneteResult(
            anciennete_inconnue=True,
            message="Date d'obtention du permis B non disponible.",
        )

    # Exemption avant 01/03/1980
    if date_obtention_b < date(1980, 3, 1):
        return AncienneteResult(
            exempt_formation=True,
            date_obtention_b=date_obtention_b.strftime("%d/%m/%Y"),
            message=f"Permis B obtenu le {date_obtention_b.strftime('%d/%m/%Y')} (avant le 01/03/1980) — exempt de formation 7h.",
        )

    # Date de référence
    date_eligible = date(date_obtention_b.year + 2, date_obtention_b.month, date_obtention_b.day)
    date_reference = date_attestation or date.today()
    ref_label = f"date attestation ({date_reference.strftime('%d/%m/%Y')})" if date_attestation else "aujourd'hui"

    # Ancienneté en années/mois
    annees = date_reference.year - date_obtention_b.year
    mois = date_reference.month - date_obtention_b.month
    if date_reference.day < date_obtention_b.day:
        mois -= 1
    if mois < 0:
        annees -= 1
        mois += 12

    db_fmt = date_obtention_b.strftime("%d/%m/%Y")
    de_fmt = date_eligible.strftime("%d/%m/%Y")

    if date_reference >= date_eligible:
        return AncienneteResult(
            eligible_formation_7h=True,
            date_obtention_b=db_fmt, date_eligible=de_fmt,
            anciennete_annees=annees, anciennete_mois=mois,
            message=f"Permis B obtenu le {db_fmt} ({annees} ans et {mois} mois à {ref_label}). Éligible à la formation 7h.",
        )

    if date_attestation and date_reference < date_eligible:
        return AncienneteResult(
            attestation_invalide=True,
            date_obtention_b=db_fmt, date_eligible=de_fmt,
            message=f"Attestation invalide : le permis B n'avait pas 2 ans au moment de la formation.",
            action="Un permis A1 est requis.",
        )

    return AncienneteResult(
        date_obtention_b=db_fmt, date_eligible=de_fmt,
        anciennete_annees=annees, anciennete_mois=mois,
        message=f"Permis B obtenu le {db_fmt} — ancienneté insuffisante ({annees} an(s) et {mois} mois). Éligible à partir du {de_fmt}.",
    )


def get_client_age(date_naissance: date | None) -> int | None:
    """Calcule l'âge du client en années civiles."""
    if not date_naissance:
        return None
    today = date.today()
    age = today.year - date_naissance.year
    if (today.month, today.day) < (date_naissance.month, date_naissance.day):
        age -= 1
    return age


