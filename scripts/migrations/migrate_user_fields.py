"""
Migration: Add current_hp and last_character_change to users
"""
from database import Database
from sqlalchemy import text

def migrate():
    db = Database()
    session = db.get_session()
    
    try:
        # Check and add current_hp column
        result = session.execute(text("PRAGMA table_info(utente)"))
        columns = [row[1] for row in result]
        
        if 'current_hp' not in columns:
            print("Adding current_hp column to utente...")
            session.execute(text("ALTER TABLE utente ADD COLUMN current_hp INTEGER"))
            session.commit()
            print("✅ current_hp column added")
        else:
            print("⏭️  current_hp column already exists")
        
        # Check and add last_character_change column
        result = session.execute(text("PRAGMA table_info(utente)"))
        columns = [row[1] for row in result]
        
        if 'last_character_change' not in columns:
            print("Adding last_character_change column to utente...")
            session.execute(text("ALTER TABLE utente ADD COLUMN last_character_change DATE"))
            session.commit()
            print("✅ last_character_change column added")
        else:
            print("⏭️  last_character_change column already exists")
        
        print("\n✅ Migration completed successfully!")
    
    except Exception as e:
        print(f"❌ Migration failed: {e}")
        session.rollback()
    finally:
        session.close()

if __name__ == "__main__":
    print("Starting user fields migration...")
    migrate()
