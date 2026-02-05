
import os
import sys
from sqlalchemy import text, inspect
sys.path.append(os.getcwd())
from database import Database

def repair():
    db = Database()
    engine = db.engine
    
    print("Starting database repair...")
    
    with engine.connect() as conn:
        inspector = inspect(engine)
        
        # 1. Fix 'utente' table
        print("Checking 'utente' table...")
        columns = [c['name'] for c in inspector.get_columns('utente')]
        stat_cols = {
            'stat_points': 'INTEGER DEFAULT 0',
            'allocated_health': 'INTEGER DEFAULT 0',
            'allocated_mana': 'INTEGER DEFAULT 0',
            'allocated_damage': 'INTEGER DEFAULT 0',
            'allocated_speed': 'INTEGER DEFAULT 0',
            'allocated_resistance': 'INTEGER DEFAULT 0',
            'allocated_crit': 'INTEGER DEFAULT 0'
        }
        
        for col, col_type in stat_cols.items():
            if col not in columns:
                print(f"  Adding missing column utente.{col}...")
                conn.execute(text(f"ALTER TABLE utente ADD COLUMN {col} {col_type}"))
            else:
                print(f"  Column utente.{col} already exists.")
        
        # 2. Fix 'guilds' table
        print("\nChecking 'guilds' table...")
        columns = [c['name'] for c in inspector.get_columns('guilds')]
        guild_cols = {
            'emblem': 'VARCHAR(255)',
            'skin_id': 'VARCHAR(64)',
            'description': 'VARCHAR(512)'
        }
        
        for col, col_type in guild_cols.items():
            if col not in columns:
                print(f"  Adding missing column guilds.{col}...")
                conn.execute(text(f"ALTER TABLE guilds ADD COLUMN {col} {col_type}"))
            else:
                print(f"  Column guilds.{col} already exists.")
        
        # 3. Clean up orphaned tables
        print("\nChecking for orphaned tables...")
        tables = inspector.get_table_names()
        if 'guild_buildings' in tables:
            print("  Dropping obsolete table 'guild_buildings'...")
            conn.execute(text("DROP TABLE guild_buildings CASCADE"))
            
        # 4. Ensure guild_dungeon_stats exists (it should if models work, but just in case)
        if 'guild_dungeon_stats' not in tables:
             print("  Warning: guild_dungeon_stats table is missing. Alembic should have created it.")
        
        conn.commit()
        print("\nDatabase repair completed successfully!")

if __name__ == "__main__":
    repair()
