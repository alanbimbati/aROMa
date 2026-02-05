
import sys
import os
from sqlalchemy import text, inspect

# Add parent dir to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import Database
from models.guild_dungeon_stats import GuildDungeonStats
from models.guild import Guild

def migrate():
    print("Starting schema migration...")
    db = Database()
    engine = db.engine
    
    with engine.connect() as conn:
        # 1. Check/Add columns to guilds table
        print("Checking 'guilds' table...")
        inspector = inspect(engine)
        columns = [c['name'] for c in inspector.get_columns('guilds')]
        
        updates = [
            ("emblem", "VARCHAR(64)"),
            ("skin_id", "VARCHAR(64)"),
            ("description", "TEXT")
        ]
        
        for col_name, col_type in updates:
            if col_name not in columns:
                print(f"Adding column '{col_name}' to guilds...")
                try:
                    conn.execute(text(f"ALTER TABLE guilds ADD COLUMN {col_name} {col_type}"))
                    conn.commit()
                except Exception as e:
                    print(f"Error adding {col_name}: {e}")
            else:
                print(f"Column '{col_name}' already exists.")

        # 2. Check/Create guild_dungeon_stats table
        print("Checking 'guild_dungeon_stats' table...")
        if not inspector.has_table("guild_dungeon_stats"):
            print("Creating 'guild_dungeon_stats' table...")
            # We can use create_all for this single table
            GuildDungeonStats.__table__.create(engine)
            print("Table created.")
        else:
            print("Table 'guild_dungeon_stats' already exists.")
            
    print("Migration complete.")

if __name__ == '__main__':
    migrate()
