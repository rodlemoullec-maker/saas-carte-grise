"""
Initialisation de la base de données — crée toutes les tables depuis les modèles ORM.

Usage : python scripts/init_db.py
"""
import asyncio
import sys
import os

# Ajouter le répertoire racine au path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from api.models.base import Base, get_engine

# Importer TOUS les modèles pour que SQLAlchemy les enregistre
from api.models.professionnel import Professionnel  # noqa
from api.models.dossier import DossierDB  # noqa
from api.models.document import DocumentDB  # noqa
from api.models.audit import AuditLog  # noqa


async def init_db():
    engine = get_engine()

    print(f"Connexion à : {engine.url}")
    print("Création des tables...")

    async with engine.begin() as conn:
        # Créer toutes les tables
        await conn.run_sync(Base.metadata.create_all)

    print("Tables créées avec succès :")
    for table_name in Base.metadata.tables:
        print(f"  ✓ {table_name}")

    await engine.dispose()
    print("\nBase de données initialisée !")


if __name__ == "__main__":
    asyncio.run(init_db())
