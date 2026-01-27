import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import Database, Base
from sqlalchemy import text
from models.dungeon_progress import DungeonProgress

def migrate():
    db = Database()
    session = db.get_session()
    engine = db.engine
    
    print("Migrating database...")
    
    # 1. Create DungeonProgress table
    try:
        DungeonProgress.__table__.create(engine)
        print("Created dungeon_progress table.")
    except Exception as e:
        print(f"Table dungeon_progress might already exist: {e}")
        
    # 2. Add columns to dungeon table
    # SQLite doesn't support IF NOT EXISTS for columns, so we try and catch
    columns = [
        ("dungeon_def_id", "INTEGER"),
        ("stats", "TEXT DEFAULT '{}'"),
        ("start_time", "DATETIME"),
        ("score", "TEXT")
    ]
    
    for col_name, col_type in columns:
        try:
            session.execute(text(f"ALTER TABLE dungeon ADD COLUMN {col_name} {col_type}"))
            print(f"Added column {col_name} to dungeon table.")
        except Exception as e:
            print(f"Column {col_name} might already exist: {e}")
            
    session.commit()
    session.close()
    print("Migration completed.")

if __name__ == "__main__":
    migrate()
