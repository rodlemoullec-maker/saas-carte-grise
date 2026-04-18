"""
Router rules — état et mise à jour des règles paramétrables.

GET   /rules/status        Version actuellement installée + date dernière vérif
POST  /rules/check-update  Vérifie auprès de l'éditeur si une nouvelle version existe
                            (force=true pour ignorer l'intervalle quotidien)
GET   /rules/inspect       Affiche le contenu actuel du bundle (debug/admin)

Note : la mise à jour effective est faite par check-update si une nouvelle
version est disponible. Aucune route séparée /apply n'est nécessaire — c'est
un acte unifié pour préserver l'intégrité (téléchargement → vérification
signature → écriture → reload).
"""
from __future__ import annotations

import logging

from fastapi import APIRouter, Query

from engine.rules.loader import get_current_bundle
from engine.rules.updater import check_for_updates, get_update_status

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/rules", tags=["rules"])


@router.get("/status")
async def rules_status():
    """État actuel des règles paramétrables installées sur cette machine."""
    return get_update_status()


@router.post("/check-update")
async def check_rules_update(force: bool = Query(default=False)):
    """
    Vérifie auprès de l'éditeur s'il existe une nouvelle version du bundle.

    Args:
        force: si True, ignore l'intervalle quotidien et force la vérification

    Returns:
        UpdateResult.to_dict() avec status (updated|up_to_date|skipped|error),
        version actuelle, version disponible, message lisible.
    """
    result = await check_for_updates(force=force)
    return result.to_dict()


@router.get("/inspect")
async def inspect_bundle():
    """
    Affiche le contenu complet du bundle actuellement chargé.

    Utile pour vérifier les valeurs actives (seuils OCR, tarifs régionaux,
    barème malus CO2, etc.).
    """
    bundle = get_current_bundle()
    return bundle.to_dict()
