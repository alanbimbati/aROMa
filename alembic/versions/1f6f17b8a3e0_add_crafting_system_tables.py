"""add_crafting_system_tables

Revision ID: 1f6f17b8a3e0
Revises: bc596a4202cf
Create Date: 2026-02-02 18:00:38.777177

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '1f6f17b8a3e0'
down_revision: Union[str, Sequence[str], None] = 'bc596a4202cf'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema - Add crafting system tables and columns."""
    
    # Create equipment table
    op.create_table(
        'equipment',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('slot', sa.String(length=50), nullable=False),
        sa.Column('rarity', sa.Integer(), nullable=False),
        sa.Column('stats_json', sa.JSON(), nullable=True),
        sa.Column('min_level', sa.Integer(), server_default='1', nullable=True),
        sa.Column('effect_type', sa.String(length=50), nullable=True),
        sa.Column('description', sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )

    # Create user_equipment table
    op.create_table(
        'user_equipment',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.BigInteger(), nullable=False),
        sa.Column('equipment_id', sa.Integer(), nullable=False),
        sa.Column('equipped', sa.Boolean(), server_default='false', nullable=True),
        sa.Column('slot_equipped', sa.String(length=50), nullable=True),
        sa.Column('created_at', sa.TIMESTAMP(), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['utente.id_Telegram'], ),
        sa.ForeignKeyConstraint(['equipment_id'], ['equipment.id'], ),
        sa.PrimaryKeyConstraint('id')
    )

    # Create resources table
    op.create_table(
        'resources',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('rarity', sa.Integer(), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('drop_source', sa.String(length=20), server_default='mob', nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('name')
    )
    
    # Create user_resources table
    op.create_table(
        'user_resources',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.BigInteger(), nullable=False),
        sa.Column('resource_id', sa.Integer(), nullable=False),
        sa.Column('quantity', sa.Integer(), server_default='0', nullable=True),
        sa.Column('source', sa.String(length=20), server_default='drop', nullable=True),
        sa.Column('created_at', sa.TIMESTAMP(), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create crafting_queue table
    op.create_table(
        'crafting_queue',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('guild_id', sa.BigInteger(), nullable=False),
        sa.Column('user_id', sa.BigInteger(), nullable=False),
        sa.Column('equipment_id', sa.Integer(), nullable=False),
        sa.Column('start_time', sa.TIMESTAMP(), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=True),
        sa.Column('completion_time', sa.TIMESTAMP(), nullable=True),
        sa.Column('status', sa.String(length=20), server_default='in_progress', nullable=True),
        sa.Column('actual_rarity', sa.Integer(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create guild_buildings table
    op.create_table(
        'guild_buildings',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('guild_id', sa.BigInteger(), nullable=False),
        sa.Column('building_type', sa.String(length=50), nullable=False),
        sa.Column('level', sa.Integer(), server_default='1', nullable=True),
        sa.Column('created_at', sa.TIMESTAMP(), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Add crafting columns to equipment table
    op.add_column('equipment', sa.Column('crafting_time', sa.Integer(), nullable=True))
    op.add_column('equipment', sa.Column('crafting_requirements', sa.Text(), nullable=True))


def downgrade() -> None:
    """Downgrade schema - Remove crafting system changes."""
    
    # Remove columns from equipment
    op.drop_column('equipment', 'crafting_requirements')
    op.drop_column('equipment', 'crafting_time')
    
    # Drop tables in reverse order
    op.drop_table('guild_buildings')
    op.drop_table('crafting_queue')
    op.drop_table('user_resources')
    op.drop_table('resources')
