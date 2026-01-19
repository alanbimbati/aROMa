import sys
import os
sys.path.append(os.getcwd())

from database import Database
from sqlalchemy import text

def migrate_aggro_system():
    db = Database()
    session = db.get_session()
    try:
        print("Migrating Aggro System...")
        
        # Check if columns exist
        try:
            session.execute(text("SELECT aggro_target_id FROM mob LIMIT 1"))
            print("Column aggro_target_id already exists.")
        except Exception:
            print("Adding aggro_target_id column...")
            session.execute(text("ALTER TABLE mob ADD COLUMN aggro_target_id INTEGER NULL"))
            
        try:
            session.execute(text("SELECT aggro_end_time FROM mob LIMIT 1"))
            print("Column aggro_end_time already exists.")
        except Exception:
            print("Adding aggro_end_time column...")
            session.execute(text("ALTER TABLE mob ADD COLUMN aggro_end_time DATETIME NULL"))
            
        session.commit()
        print("Migration completed successfully.")
        
    except Exception as e:
        print(f"Migration failed: {e}")
        session.rollback()
    finally:
        session.close()

if __name__ == "__main__":
    migrate_aggro_system()
