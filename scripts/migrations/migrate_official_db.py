import sqlite3
import os
import shutil
import datetime
from sqlalchemy import create_engine, text
from database import Base, Database

# Import all models to ensure they are registered with Base.metadata
from models.user import Utente, Admin
from models.system import Livello, CharacterAbility, CharacterTransformation, UserTransformation, Domenica, UserCharacter
from models.achievements import Achievement, UserAchievement, GameEvent
from models.seasons import Season, SeasonProgress, SeasonReward
from models.combat import MobAbility, CombatParticipation
from models.pve import Mob, Raid, RaidParticipation
from models.items import Collezionabili
from models.game import GiocoUtente
from models.legacy_tables import Points, Gruppo, GiocoAroma

DB_NAME = "points_official.db"
BACKUP_NAME = f"points_official_backup_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.db"

def backup_db():
    if os.path.exists(DB_NAME):
        print(f"Creating backup: {BACKUP_NAME}")
        shutil.copy2(DB_NAME, BACKUP_NAME)
        return True
    else:
        print(f"Error: {DB_NAME} not found!")
        return False

def add_column(cursor, table, column, col_type):
    try:
        cursor.execute(f"ALTER TABLE {table} ADD COLUMN {column} {col_type}")
        print(f"Added column {column} to {table}")
    except sqlite3.OperationalError as e:
        if "duplicate column name" in str(e):
            print(f"Column {column} already exists in {table}")
        else:
            print(f"Error adding column {column} to {table}: {e}")

def migrate():
    if not backup_db():
        return

    print("Starting migration of points_official.db...")
    
    # 1. Add missing columns using raw SQLite (SQLAlchemy ALTER TABLE is limited)
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    # Utente table
    add_column(cursor, "utente", "current_mana", "INTEGER DEFAULT 50")
    add_column(cursor, "utente", "active_status_effects", "TEXT")
    add_column(cursor, "utente", "title", "VARCHAR")
    add_column(cursor, "utente", "titles", "TEXT")
    
    # Livello table
    add_column(cursor, "livello", "price", "INTEGER DEFAULT 0")
    add_column(cursor, "livello", "elemental_type", "VARCHAR DEFAULT 'Normal'")
    add_column(cursor, "livello", "crit_chance", "INTEGER DEFAULT 5")
    add_column(cursor, "livello", "crit_multiplier", "FLOAT DEFAULT 1.5")
    add_column(cursor, "livello", "required_character_id", "INTEGER")
    add_column(cursor, "livello", "special_attack_name", "VARCHAR")
    add_column(cursor, "livello", "special_attack_damage", "INTEGER DEFAULT 0")
    add_column(cursor, "livello", "special_attack_mana_cost", "INTEGER DEFAULT 0")
    add_column(cursor, "livello", "image_path", "VARCHAR")
    add_column(cursor, "livello", "telegram_file_id", "VARCHAR")
    add_column(cursor, "livello", "description", "VARCHAR")
    add_column(cursor, "livello", "character_group", "VARCHAR DEFAULT 'General'")
    
    # Mob table
    add_column(cursor, "mob", "passive_abilities", "TEXT")
    add_column(cursor, "mob", "active_abilities", "TEXT")
    add_column(cursor, "mob", "ai_behavior", "VARCHAR DEFAULT 'aggressive'")
    add_column(cursor, "mob", "phase_thresholds", "TEXT")
    add_column(cursor, "mob", "current_phase", "INTEGER DEFAULT 1")
    add_column(cursor, "mob", "active_buffs", "TEXT")
    
    # Character Ability table
    add_column(cursor, "character_ability", "status_effect", "VARCHAR")
    add_column(cursor, "character_ability", "status_chance", "INTEGER DEFAULT 0")
    add_column(cursor, "character_ability", "status_duration", "INTEGER DEFAULT 0")
    
    conn.commit()
    conn.close()
    
    # 2. Create missing tables using SQLAlchemy
    # We need to temporarily point Database to points_official.db
    engine = create_engine(f'sqlite:///{DB_NAME}')
    print("Creating missing tables...")
    Base.metadata.create_all(engine)
    
    print("Migration completed successfully!")

if __name__ == "__main__":
    migrate()
