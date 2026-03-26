"""
Estimation des taxes d'immatriculation (indicatif, non contractuel).

Composantes :
  Y1 — Taxe régionale (puissance fiscale x tarif CV du département)
  Y2 — Taxe formation professionnelle (VU > 3,5T uniquement — hors périmètre VP/moto)
  Y3 — Malus écologique CO2 (barème WLTP 2026)
  Y4 — Taxe de gestion (11€ fixe, exonéré si électrique)
  Y5 — Redevance d'acheminement (2,76€ fixe)
  Y6 — Malus au poids (> 1800 kg, barème 2026)

Note : le montant FINAL est confirmé par le SIV à la soumission.
L'estimation affichée en Phase 1 est INDICATIVE.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any


# Tarif par CV par département (extrait — à compléter avec les 101 départements)
# Source : barème 2026 (à mettre à jour chaque année)
TARIF_CV_PAR_DEPARTEMENT: dict[str, float] = {
    "01": 43.00, "02": 33.00, "03": 43.00, "04": 51.20, "05": 51.20,
    "06": 51.20, "07": 43.00, "08": 33.00, "09": 44.00, "10": 33.00,
    "11": 44.00, "12": 44.00, "13": 51.20, "14": 35.00, "15": 43.00,
    "16": 45.00, "17": 45.00, "18": 49.00, "19": 43.00, "20": 27.00,
    "21": 51.00, "22": 51.00, "23": 43.00, "24": 45.00, "25": 51.00,
    "26": 51.20, "27": 35.00, "28": 49.00, "29": 51.00, "30": 44.00,
    "31": 44.00, "32": 44.00, "33": 51.00, "34": 44.00, "35": 51.00,
    "36": 49.00, "37": 49.00, "38": 43.00, "39": 51.00, "40": 44.00,
    "41": 49.00, "42": 43.00, "43": 43.00, "44": 51.00, "45": 49.00,
    "46": 44.00, "47": 45.00, "48": 44.00, "49": 51.00, "50": 35.00,
    "51": 33.00, "52": 33.00, "53": 51.00, "54": 33.00, "55": 33.00,
    "56": 51.00, "57": 33.00, "58": 51.00, "59": 53.00, "60": 33.00,
    "61": 35.00, "62": 33.00, "63": 43.00, "64": 44.00, "65": 44.00,
    "66": 44.00, "67": 48.00, "68": 48.00, "69": 43.00, "70": 51.00,
    "71": 51.00, "72": 51.00, "73": 43.00, "74": 43.00, "75": 46.15,
    "76": 35.00, "77": 46.15, "78": 46.15, "79": 45.00, "80": 33.00,
    "81": 44.00, "82": 44.00, "83": 51.20, "84": 51.20, "85": 51.00,
    "86": 45.00, "87": 43.00, "88": 33.00, "89": 51.00, "90": 51.00,
    "91": 46.15, "92": 46.15, "93": 46.15, "94": 46.15, "95": 46.15,
    "971": 41.00, "972": 30.00, "973": 42.50, "974": 51.00, "976": 30.00,
    "2A": 27.00, "2B": 27.00,
}

# Barème malus CO2 WLTP 2026 (seuils simplifiés — à mettre à jour)
# Format : (seuil_min_g_km, seuil_max_g_km, montant_euros)
MALUS_CO2_2026: list[tuple[int, int, int]] = [
    (118, 118, 50),
    (119, 119, 75),
    (120, 120, 100),
    (121, 121, 125),
    (122, 122, 150),
    (123, 130, 170),
    (131, 140, 400),
    (141, 150, 1000),
    (151, 160, 3000),
    (161, 170, 5000),
    (171, 180, 8000),
    (181, 190, 12000),
    (191, 200, 18000),
    (201, 210, 25000),
    (211, 220, 30000),
    (221, 230, 40000),
    (231, 999, 60000),
]

# Malus au poids (barème 2026)
SEUIL_POIDS_KG = 1800
TARIF_POIDS_PAR_KG = 10  # €/kg au-dessus du seuil


TAXE_GESTION = 11.00       # Y4 — fixe (exonéré électrique)
REDEVANCE_ACHEMINEMENT = 2.76  # Y5 — fixe


@dataclass
class TaxEstimation:
    y1_taxe_regionale: float = 0.0
    y3_malus_co2: float = 0.0
    y4_taxe_gestion: float = 0.0
    y5_redevance: float = REDEVANCE_ACHEMINEMENT
    y6_malus_poids: float = 0.0
    total: float = 0.0
    is_estimate: bool = True  # Toujours True — montant final = SIV
    notes: list[str] | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "y1_taxe_regionale": self.y1_taxe_regionale,
            "y3_malus_co2": self.y3_malus_co2,
            "y4_taxe_gestion": self.y4_taxe_gestion,
            "y5_redevance": self.y5_redevance,
            "y6_malus_poids": self.y6_malus_poids,
            "total": self.total,
            "is_estimate": self.is_estimate,
            "notes": self.notes or [],
        }


class TaxCalculator:
    """Calcul indicatif des taxes d'immatriculation."""

    def estimate(self, docs: Any) -> dict[str, Any]:
        """
        Calcule l'estimation à partir des documents extraits.

        Attend un objet ExtractedDocuments (engine/pipeline/phase1.py).
        """
        notes: list[str] = []
        estimation = TaxEstimation(notes=notes)

        # Département client (depuis le Cerfa ou le domicile)
        departement = self._get_departement(docs)

        # Puissance fiscale (COC ou Cerfa)
        puissance_cv = self._get_puissance_cv(docs)

        # CO2 WLTP
        co2_wltp = self._get_co2_wltp(docs)

        # Énergie
        energie = self._get_energie(docs)
        is_electrique = energie in ("electrique",) if energie else False

        # PTAC (pour malus poids)
        ptac_kg = None
        if docs.coc and docs.coc.ptac_kg:
            ptac_kg = docs.coc.ptac_kg

        # ─── Y1 : Taxe régionale ─────────────────────────────────────────
        if departement and puissance_cv:
            tarif = TARIF_CV_PAR_DEPARTEMENT.get(departement)
            if tarif:
                estimation.y1_taxe_regionale = tarif * puissance_cv
                if is_electrique:
                    # Exonération totale ou partielle selon région
                    estimation.y1_taxe_regionale = 0.0
                    notes.append("Véhicule électrique — exonération taxe régionale")
            else:
                notes.append(f"Département {departement!r} non trouvé — taxe régionale non calculée")
        else:
            notes.append("Puissance fiscale ou département inconnu — taxe régionale non calculée")

        # ─── Y3 : Malus CO2 ──────────────────────────────────────────────
        if co2_wltp and co2_wltp > 0 and not is_electrique:
            for seuil_min, seuil_max, montant in MALUS_CO2_2026:
                if seuil_min <= co2_wltp <= seuil_max:
                    estimation.y3_malus_co2 = montant
                    break
            if estimation.y3_malus_co2 == 0 and co2_wltp >= 118:
                estimation.y3_malus_co2 = MALUS_CO2_2026[-1][2]
                notes.append(f"CO2 WLTP={co2_wltp} g/km — malus plafonné")
        elif co2_wltp and co2_wltp < 118:
            notes.append(f"CO2 WLTP={co2_wltp} g/km — pas de malus")
        elif is_electrique:
            notes.append("Véhicule électrique — pas de malus CO2")

        # ─── Y4 : Taxe de gestion ────────────────────────────────────────
        estimation.y4_taxe_gestion = 0.0 if is_electrique else TAXE_GESTION

        # ─── Y5 : Redevance acheminement ─────────────────────────────────
        estimation.y5_redevance = REDEVANCE_ACHEMINEMENT

        # ─── Y6 : Malus au poids ─────────────────────────────────────────
        if ptac_kg and ptac_kg > SEUIL_POIDS_KG and not is_electrique:
            estimation.y6_malus_poids = (ptac_kg - SEUIL_POIDS_KG) * TARIF_POIDS_PAR_KG
            notes.append(f"PTAC={ptac_kg} kg > {SEUIL_POIDS_KG} kg — malus poids appliqué")

        # ─── Total ────────────────────────────────────────────────────────
        estimation.total = (
            estimation.y1_taxe_regionale
            + estimation.y3_malus_co2
            + estimation.y4_taxe_gestion
            + estimation.y5_redevance
            + estimation.y6_malus_poids
        )

        notes.append("Estimation INDICATIVE — montant final confirmé par le SIV à la soumission")

        return estimation.to_dict()

    def _get_departement(self, docs) -> str | None:
        if docs.cerfa and docs.cerfa.code_postal:
            cp = docs.cerfa.code_postal
            if cp.startswith("97") or cp.startswith("98"):
                return cp[:3]
            if cp.startswith("20"):
                # Corse
                return "2A" if int(cp) < 20200 else "2B"
            return cp[:2]
        if docs.domicile and docs.domicile.code_postal:
            return docs.domicile.code_postal[:2]
        return None

    def _get_puissance_cv(self, docs) -> int | None:
        if docs.coc and docs.coc.puissance_fiscale_cv:
            return docs.coc.puissance_fiscale_cv
        if docs.cerfa and docs.cerfa.puissance_fiscale_cv:
            return docs.cerfa.puissance_fiscale_cv
        return None

    def _get_co2_wltp(self, docs) -> float | None:
        if docs.coc and docs.coc.co2_wltp:
            return docs.coc.co2_wltp
        return None

    def _get_energie(self, docs) -> str | None:
        from engine.normalizers.vehicles import normalize_energie
        if docs.coc and docs.coc.energie:
            return normalize_energie(docs.coc.energie)
        return None
