"""
Normalisation et comparaison de noms de personnes.
"""
from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass


@dataclass
class NameMatchResult:
    matched: bool
    confidence: float       # 0.0 – 1.0
    method: str             # exact | normalized | fuzzy | partial
    note: str | None = None


def normalize_name(name: str) -> str:
    name = unicodedata.normalize("NFKD", name)
    name = "".join(c for c in name if not unicodedata.combining(c))
    name = name.upper().replace("-", " ").replace("'", " ")
    name = re.sub(r"\s+", " ", name).strip()
    return name


def fuzzy_ratio(a: str, b: str) -> float:
    """Distance de Levenshtein normalisée. TODO: remplacer par fuzzywuzzy en prod."""
    if a == b:
        return 1.0
    len_a, len_b = len(a), len(b)
    if len_a == 0 or len_b == 0:
        return 0.0
    matrix = [[0] * (len_b + 1) for _ in range(len_a + 1)]
    for i in range(len_a + 1):
        matrix[i][0] = i
    for j in range(len_b + 1):
        matrix[0][j] = j
    for i in range(1, len_a + 1):
        for j in range(1, len_b + 1):
            cost = 0 if a[i - 1] == b[j - 1] else 1
            matrix[i][j] = min(matrix[i - 1][j] + 1, matrix[i][j - 1] + 1, matrix[i - 1][j - 1] + cost)
    return 1.0 - matrix[len_a][len_b] / max(len_a, len_b)


def match_names(name_a: str, name_b: str) -> NameMatchResult:
    """
    Seuils opérationnels :
    ≥ 0.97 → match auto (diff OCR probable)
    0.85–0.96 → match probable, vérification recommandée
    0.70–0.84 → incertitude → correction demandée
    < 0.70 → non-match
    """
    na, nb = normalize_name(name_a), normalize_name(name_b)

    if na == nb:
        return NameMatchResult(matched=True, confidence=1.0, method="exact")

    if set(na.split()) == set(nb.split()) and len(na.split()) > 1:
        return NameMatchResult(matched=True, confidence=0.97, method="normalized",
                               note="Ordre des composantes différent")

    ratio = fuzzy_ratio(na, nb)
    if ratio >= 0.97:
        return NameMatchResult(matched=True, confidence=ratio, method="fuzzy")
    elif ratio >= 0.85:
        return NameMatchResult(matched=True, confidence=ratio, method="fuzzy",
                               note="Vérification visuelle recommandée")
    elif ratio >= 0.70:
        return NameMatchResult(matched=False, confidence=ratio, method="fuzzy",
                               note="Incertitude — correction demandée")
    return NameMatchResult(matched=False, confidence=ratio, method="fuzzy", note="Noms différents")
