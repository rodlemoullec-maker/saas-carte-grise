"""baseline tous modeles

Revision ID: 2210fe3b07be
Revises:
Create Date: 2026-04-05 01:02:50.549717

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '2210fe3b07be'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Ajout password_hash + normalisation contraintes."""
    # Nouvelle colonne pour l'auth JWT
    op.add_column('professionnels', sa.Column('password_hash', sa.String(length=255), nullable=True))

    # Normaliser les NOT NULL (le code Python les declare non-nullable)
    op.alter_column('professionnels', 'type_compte',
               existing_type=sa.VARCHAR(length=30),
               nullable=False,
               existing_server_default=sa.text("'VENDEUR_HABILITE'::character varying"))
    op.alter_column('professionnels', 'page_publique_active',
               existing_type=sa.BOOLEAN(),
               nullable=False,
               existing_server_default=sa.text('false'))
    op.alter_column('professionnels', 'cgv_acceptees',
               existing_type=sa.BOOLEAN(),
               nullable=False,
               existing_server_default=sa.text('false'))
    op.alter_column('dossiers', 'created_by_source',
               existing_type=sa.VARCHAR(length=10),
               nullable=False,
               existing_server_default=sa.text("'PRO'::character varying"))

    # Index unique sur slug (remplacement de la contrainte unique)
    op.create_index(op.f('ix_professionnels_slug'), 'professionnels', ['slug'], unique=True)


def downgrade() -> None:
    """Retour arriere."""
    op.drop_index(op.f('ix_professionnels_slug'), table_name='professionnels')
    op.alter_column('dossiers', 'created_by_source',
               existing_type=sa.VARCHAR(length=10),
               nullable=True,
               existing_server_default=sa.text("'PRO'::character varying"))
    op.alter_column('professionnels', 'cgv_acceptees',
               existing_type=sa.BOOLEAN(),
               nullable=True,
               existing_server_default=sa.text('false'))
    op.alter_column('professionnels', 'page_publique_active',
               existing_type=sa.BOOLEAN(),
               nullable=True,
               existing_server_default=sa.text('false'))
    op.alter_column('professionnels', 'type_compte',
               existing_type=sa.VARCHAR(length=30),
               nullable=True,
               existing_server_default=sa.text("'VENDEUR_HABILITE'::character varying"))
    op.drop_column('professionnels', 'password_hash')
