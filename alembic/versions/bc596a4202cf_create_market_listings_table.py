"""create_market_listings_table

Revision ID: bc596a4202cf
Revises: 26fdc4b69562
Create Date: 2026-01-31 16:17:52.500838

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'bc596a4202cf'
down_revision: Union[str, Sequence[str], None] = '26fdc4b69562'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        'market_listings',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('seller_id', sa.BigInteger(), nullable=False),
        sa.Column('item_name', sa.String(), nullable=False),
        sa.Column('quantity', sa.Integer(), nullable=True, server_default='1'),
        sa.Column('price_per_unit', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('expires_at', sa.DateTime(), nullable=True),
        sa.Column('status', sa.String(), nullable=True, server_default='active'),
        sa.Column('buyer_id', sa.BigInteger(), nullable=True),
        sa.Column('sold_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['buyer_id'], ['utente.id_Telegram'], ),
        sa.ForeignKeyConstraint(['seller_id'], ['utente.id_Telegram'], ),
        sa.PrimaryKeyConstraint('id')
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table('market_listings')
