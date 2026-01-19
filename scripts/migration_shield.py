import sys
import os
sys.path.append(os.getcwd())

from database import Database
from sqlalchemy import text

def migrate_shield_system():
    db = Database()
    session = db.get_session()
    try:
        print("Migrating Shield System...")
        
        # Check if columns exist
        try:
            session.execute(text("SELECT shield_hp FROM utente LIMIT 1"))
            print("Column shield_hp already exists.")
        except Exception:
            print("Adding shield_hp column...")
            session.execute(text("ALTER TABLE utente ADD COLUMN shield_hp INTEGER DEFAULT 0"))
            
        try:
            session.execute(text("SELECT shield_max_hp FROM utente LIMIT 1"))
            print("Column shield_max_hp already exists.")
        except Exception:
            print("Adding shield_max_hp column...")
            session.execute(text("ALTER TABLE utente ADD COLUMN shield_max_hp INTEGER DEFAULT 0"))
            
        try:
            session.execute(text("SELECT shield_end_time FROM utente LIMIT 1"))
            print("Column shield_end_time already exists.")
        except Exception:
            print("Adding shield_end_time column...")
            session.execute(text("ALTER TABLE utente ADD COLUMN shield_end_time DATETIME NULL"))
            
        # Also add last_shield_cast for cooldown tracking
        try:
            session.execute(text("SELECT last_shield_cast FROM utente LIMIT 1"))
            print("Column last_shield_cast already exists.")
        except Exception:
            print("Adding last_shield_cast column...")
            session.execute(text("ALTER TABLE utente ADD COLUMN last_shield_cast DATETIME NULL"))
            
        session.commit()
        print("Migration completed successfully.")
        
    except Exception as e:
        print(f"Migration failed: {e}")
        session.rollback()
    finally:
        session.close()

if __name__ == "__main__":
    migrate_shield_system()
