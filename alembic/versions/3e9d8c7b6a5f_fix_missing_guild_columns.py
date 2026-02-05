"""fix_missing_guild_columns

Revision ID: 3e9d8c7b6a5f
Revises: 26591ffe417c
Create Date: 2026-02-05 11:25:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '3e9d8c7b6a5f'
down_revision: Union[str, Sequence[str], None] = '26591ffe417c'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    columns = [c['name'] for c in inspector.get_columns('guilds')]
    
    if 'emblem' not in columns:
        op.add_column('guilds', sa.Column('emblem', sa.String(length=255), nullable=True))
    if 'skin_id' not in columns:
        op.add_column('guilds', sa.Column('skin_id', sa.String(length=64), nullable=True))
    if 'description' not in columns:
        op.add_column('guilds', sa.Column('description', sa.String(length=512), nullable=True))

def downgrade() -> None:
    op.drop_column('guilds', 'description')
    op.drop_column('guilds', 'skin_id')
    op.drop_column('guilds', 'emblem')
