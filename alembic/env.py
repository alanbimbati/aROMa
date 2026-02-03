from logging.config import fileConfig

from sqlalchemy import engine_from_config
from sqlalchemy import pool

from alembic import context

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
# import sys/path to be able to import from parent directory
import sys
import os
sys.path.append(os.getcwd())

from database import Base, Database
from database import Base, Database
# Import all models to ensure they are registered in Base.metadata
from models.user import Utente, Admin
from models.market import MarketListing
from models.achievements import Achievement, UserAchievement, GameEvent # GameEvent here
from models.character_ownership import CharacterOwnership
from models.combat import CombatParticipation, MobAbility
from models.dungeon import Dungeon, DungeonParticipant
from models.dungeon_progress import DungeonProgress
from models.game import GameInfo, Steam, NomiGiochi, GiocoUtente # Corrected
from models.guild import Guild, GuildMember, GuildUpgrade, GuildItem
from models.inventory import UserItem
from models.item import Item, ItemSet
from models.items import Collezionabili
from models.legacy_tables import Points, Gruppo, GiocoAroma
from models.pve import Mob, Raid, RaidParticipation
from models.seasons import Season, SeasonReward, SeasonClaimedReward, SeasonProgress
from models.stats import UserStat
from models.system import Livello, UserCharacter, Domenica
from models.system_state import SystemState
from models.equipment import Equipment, UserEquipment
from models.crafting import CraftingQueue
from models.resources import Resource, UserResource

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Interpret the config file for Python logging.
# This line sets up loggers basically.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# add your model's MetaData object here
# for 'autogenerate' support
target_metadata = Base.metadata

# Get connection string from Database class logic
# We instantiate Database just to ensure env vars are loaded and URL is constructed?
# Or we replicate the logic. Database() singleton might initialize engine.
# Let's peek at the URL from the engine if possible or reconstruct it.
# Reconstructing is safer to avoid side effects of Database() init if any (like print statements).
# BUT Database() init prints connection string info which is useful.

# Let's use the Database singleton's engine URL.
db_instance = Database()
db_url = str(db_instance.engine.url)

# Override sqlalchemy.url in config
config.set_main_option("sqlalchemy.url", db_url)


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well.  By skipping the Engine creation
    we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.

    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode.

    In this scenario we need to create an Engine
    and associate a connection with the context.

    """
    # Use the engine from our Database class instead of creating a new one from config
    # This ensures consistency with the app (e.g. pool settings, driver args)
    connectable = db_instance.engine

    with connectable.connect() as connection:
        context.configure(
            connection=connection, target_metadata=target_metadata
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
