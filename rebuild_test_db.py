
import os
import sys

# Force test mode
os.environ['TEST_DB'] = '1'

# Add parent dir to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '.')))

from database import Database, Base
from models import user, guild, dungeon, equipment, pve, combat, resources, market, guild_dungeon_stats

def rebuild():
    print("Rebuilding Test Database...")
    db = Database()
    session = db.get_session()
    engine = db.engine
    
    print(f"Connected to: {engine.url.database}")
    if 'test' not in engine.url.database:
        print("SAFETY CHECK FAILED: Not a test database!")
        return

    print("Dropping all tables...")
    Base.metadata.drop_all(engine)
    
    print("Creating all tables...")
    Base.metadata.create_all(engine)
    
    print("Done.")

if __name__ == "__main__":
    rebuild()
