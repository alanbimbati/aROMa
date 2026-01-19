import sqlite3
from database import Database
from sqlalchemy import text
import os

SOURCE_DB = "points_fix_source.db"
TARGET_DB = "points_final.db"

def migrate_table(table_name):
    print(f"Migrating {table_name}...")
    
    if not os.path.exists(SOURCE_DB):
        print(f"Source DB {SOURCE_DB} not found!")
        return

    # Connect to source
    src_conn = sqlite3.connect(SOURCE_DB)
    src_conn.row_factory = sqlite3.Row
    src_cursor = src_conn.cursor()
    
    try:
        src_cursor.execute(f"SELECT * FROM {table_name}")
        rows = src_cursor.fetchall()
    except Exception as e:
        print(f"Skipping {table_name}: {e}")
        return

    if not rows:
        print(f"No data in {table_name}")
        return

    # Get column names from source
    source_columns = set(rows[0].keys())
    
    # Connect to target via SQLAlchemy
    db = Database() # Points to TARGET_DB via database.py config
    session = db.get_session()
    
    # Get target columns
    tgt_conn = sqlite3.connect(TARGET_DB)
    tgt_cursor = tgt_conn.cursor()
    tgt_cursor.execute(f"PRAGMA table_info({table_name})")
    tgt_cols_info = tgt_cursor.fetchall()
    tgt_columns = set([c[1] for c in tgt_cols_info])
    tgt_conn.close()
    
    # Intersect
    common_columns = list(source_columns.intersection(tgt_columns))
    
    if not common_columns:
        print(f"No common columns for {table_name}")
        return
        
    print(f"Migrating {len(common_columns)} columns for {table_name}")
    
    # Prepare insert statement
    cols_str = ", ".join(common_columns)
    params_str = ", ".join([f":{c}" for c in common_columns])
    sql = text(f"INSERT INTO {table_name} ({cols_str}) VALUES ({params_str})")
    
    count = 0
    for row in rows:
        data = dict(row)
        try:
            session.execute(sql, data)
            count += 1
        except Exception as e:
            # print(f"Error inserting row in {table_name}: {e}")
            pass
            
    session.commit()
    session.close()
    print(f"Migrated {count} rows to {table_name}")

if __name__ == "__main__":
    # List of tables to migrate
    tables = [
        "utente", "guilds", "guild_members", "guild_upgrades", "guild_items",
        "collezionabili", "mob_ability", "combat_participation",
        "achievement", "user_achievement", "game_event",
        "character_ownership", "dungeon", "dungeon_participant",
        "games", "steam", "giocoutente", "nomigiochi",
        "mob", "raid", "raid_participation",
        "season", "season_progress", "season_reward", "season_claimed_reward",
        "user_stat",
        "livello", "character_ability", "character_transformation", "user_transformation",
        "domenica", "user_character",
        "points", "gruppo", "giocoaroma"
    ]
    
    for t in tables:
        migrate_table(t)
