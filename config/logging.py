"""
Configuration du logging structuré.

TODO: configurer structlog ou loguru pour les logs JSON en production.
TODO: intégrer avec Sentry pour les erreurs.
"""
from __future__ import annotations
import logging


def setup_logging(log_level: str = "INFO") -> None:
    logging.basicConfig(
        level=getattr(logging, log_level.upper()),
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )
