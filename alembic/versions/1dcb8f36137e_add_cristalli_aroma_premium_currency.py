"""add_cristalli_aroma_premium_currency

Revision ID: 1dcb8f36137e
Revises: bee0b040d7a1
Create Date: 2026-02-07 17:43:26.009832

Premium Currency for Cosmetics:
- Name: Cristalli aROMa ✨
- Rate: 1000 satoshi (BTC) = 1 Cristallo aROMa
- Usage: Skins only (cosmetic, no gameplay advantage)
- Skin Pricing: floor(character_level / 10) cristalli
  Examples:
    - Lv 1-9: 0-1 cristalli (rounded to 1 min)
    - Lv 10-19: 1 cristallo  
    - Lv 20-29: 2 cristalli
    - Lv 50-59: 5 cristalli
    - Lv 100+: 10 cristalli

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '1dcb8f36137e'
down_revision: Union[str, Sequence[str], None] = 'bee0b040d7a1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add cristalli_aroma premium currency column."""
    # Add column to utente table
    op.add_column('utente', sa.Column('cristalli_aroma', sa.Integer(), nullable=False, server_default='0'))


def downgrade() -> None:
    """Remove cristalli_aroma column."""
    op.drop_column('utente', 'cristalli_aroma')
