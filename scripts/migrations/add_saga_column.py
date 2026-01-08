"""
Script to add 'saga' column to 'livello' table if missing
"""
import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))

from database import Database
from sqlalchemy import text

def migrate_db():
    db = Database()
    session = db.get_session()
    
    try:
        # Check if column exists
        session.execute(text("SELECT saga FROM livello LIMIT 1"))
        print("Column 'saga' already exists.")
    except Exception:
        print("Adding 'saga' column to 'livello' table...")
        try:
            session.rollback() # Clear error
            # Add column
            session.execute(text("ALTER TABLE livello ADD COLUMN saga VARCHAR(100)"))
            session.commit()
            print("Column added successfully.")
        except Exception as e:
            print(f"Error adding column: {e}")
            session.rollback()
    finally:
        session.close()

if __name__ == "__main__":
    migrate_db()
