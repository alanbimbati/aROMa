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
from models.stats import UserStat
from models.seasons import Season, SeasonProgress, SeasonReward
from models.combat import MobAbility, CombatParticipation
from models.pve import Mob, Raid, RaidParticipation
from models.dungeon import Dungeon, DungeonParticipant
from models.items import Collezionabili
from models.game import GiocoUtente
from models.legacy_tables import Points, Gruppo, GiocoAroma

DB_NAME = "points_deietpi.db"
BACKUP_NAME = f"points_deietpi_backup_fresh_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.db"

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

    print(f"Starting migration of {DB_NAME}...")
    
    # 1. Add missing columns using raw SQLite
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    # Utente table
    print("Updating utente table...")
    add_column(cursor, "utente", "chat_exp", "INTEGER DEFAULT 0")
    add_column(cursor, "utente", "daily_wumpa_earned", "INTEGER DEFAULT 0")
    add_column(cursor, "utente", "last_wumpa_reset", "DATETIME")
    
    # Mob table
    print("Updating mob table...")
    add_column(cursor, "mob", "passive_abilities", "TEXT")
    add_column(cursor, "mob", "active_abilities", "TEXT")
    add_column(cursor, "mob", "ai_behavior", "VARCHAR DEFAULT 'aggressive'")
    add_column(cursor, "mob", "phase_thresholds", "TEXT")
    add_column(cursor, "mob", "current_phase", "INTEGER DEFAULT 1")
    add_column(cursor, "mob", "active_buffs", "TEXT")
    add_column(cursor, "mob", "last_target_id", "INTEGER")
    add_column(cursor, "mob", "dungeon_id", "INTEGER")
    add_column(cursor, "mob", "chat_id", "INTEGER")
    
    # 2. Achievement System Refactor
    print("Refactoring achievement system...")
    try:
        # Create user_stat table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS user_stat (
                user_id INTEGER NOT NULL,
                stat_key VARCHAR(50) NOT NULL,
                value REAL DEFAULT 0.0,
                last_updated DATETIME DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (user_id, stat_key)
            )
        """)
        
        # Recreate game_event table if it exists (to match new schema)
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='game_event'")
        if cursor.fetchone():
            print("Recreating game_event table...")
            cursor.execute("ALTER TABLE game_event RENAME TO game_event_old")
            cursor.execute("""
                CREATE TABLE game_event (
                    id INTEGER PRIMARY KEY,
                    user_id INTEGER NOT NULL,
                    event_type VARCHAR(50) NOT NULL,
                    value REAL DEFAULT 0.0,
                    context TEXT,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    processed BOOLEAN DEFAULT FALSE
                )
            """)
        
        # Recreate achievement table
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='achievement'")
        if cursor.fetchone():
            print("Recreating achievement table...")
            cursor.execute("ALTER TABLE achievement RENAME TO achievement_old")
            cursor.execute("""
                CREATE TABLE achievement (
                    id INTEGER PRIMARY KEY,
                    achievement_key VARCHAR(50) UNIQUE NOT NULL,
                    name VARCHAR(100) NOT NULL,
                    description TEXT NOT NULL,
                    stat_key VARCHAR(50) NOT NULL,
                    condition_type VARCHAR(20) DEFAULT '>=',
                    tiers TEXT NOT NULL,
                    category VARCHAR(20),
                    icon VARCHAR(255),
                    hidden BOOLEAN DEFAULT FALSE,
                    flavor_text TEXT
                )
            """)
            
        # Recreate user_achievement table
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='user_achievement'")
        if cursor.fetchone():
            print("Recreating user_achievement table...")
            cursor.execute("ALTER TABLE user_achievement RENAME TO user_achievement_old")
            cursor.execute("""
                CREATE TABLE user_achievement (
                    user_id INTEGER NOT NULL,
                    achievement_key VARCHAR(50) NOT NULL,
                    current_tier VARCHAR(20),
                    progress_value REAL DEFAULT 0.0,
                    unlocked_at DATETIME,
                    last_progress_update DATETIME DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY (user_id, achievement_key)
                )
            """)
    except Exception as e:
        print(f"Error during achievement refactor: {e}")

    # 3. CombatParticipation Unique Constraint
    print("Updating combat_participation table...")
    try:
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='combat_participation'")
        if cursor.fetchone():
            # SQLite doesn't support ADD CONSTRAINT, must recreate table
            cursor.execute("ALTER TABLE combat_participation RENAME TO combat_participation_old")
            cursor.execute("""
                CREATE TABLE combat_participation (
                    id INTEGER PRIMARY KEY,
                    mob_id INTEGER,
                    user_id INTEGER NOT NULL,
                    damage_dealt INTEGER DEFAULT 0,
                    hits_landed INTEGER DEFAULT 0,
                    critical_hits INTEGER DEFAULT 0,
                    healing_done INTEGER DEFAULT 0,
                    buffs_applied INTEGER DEFAULT 0,
                    exp_earned INTEGER DEFAULT 0,
                    loot_received TEXT,
                    reward_claimed BOOLEAN DEFAULT FALSE,
                    first_hit_time DATETIME,
                    last_hit_time DATETIME,
                    FOREIGN KEY(mob_id) REFERENCES mob (id),
                    UNIQUE(mob_id, user_id)
                )
            """)
            # Copy data back
            cursor.execute("""
                INSERT OR IGNORE INTO combat_participation (
                    id, mob_id, user_id, damage_dealt, hits_landed, critical_hits,
                    healing_done, buffs_applied, exp_earned, loot_received,
                    reward_claimed, first_hit_time, last_hit_time
                ) SELECT 
                    id, mob_id, user_id, damage_dealt, hits_landed, critical_hits,
                    healing_done, buffs_applied, exp_earned, loot_received,
                    reward_claimed, first_hit_time, last_hit_time
                FROM combat_participation_old
            """)
    except Exception as e:
        print(f"Error updating combat_participation: {e}")

    conn.commit()
    conn.close()
    
    # 4. Create missing tables using SQLAlchemy
    engine = create_engine(f'sqlite:///{DB_NAME}')
    print("Creating missing tables and ensuring schema consistency...")
    Base.metadata.create_all(engine)
    
    print("Migration completed successfully!")

if __name__ == "__main__":
    migrate()
