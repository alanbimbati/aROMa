"""
Migration: Add required_level column to character_transformations table
"""
from database import Database
from sqlalchemy import text

def migrate():
    db = Database()
    session = db.get_session()
    
    try:
        # Check if column exists
        result = session.execute(text("PRAGMA table_info(character_transformation)"))
        columns = [row[1] for row in result]
        
        if 'required_level' not in columns:
            print("Adding required_level column to character_transformation...")
            session.execute(text("ALTER TABLE character_transformation ADD COLUMN required_level INTEGER"))
            session.commit()
            print("✅ Migration completed successfully!")
        else:
            print("⏭️  required_level column already exists, skipping migration.")
    
    except Exception as e:
        print(f"❌ Migration failed: {e}")
        session.rollback()
    finally:
        session.close()

if __name__ == "__main__":
    print("Starting migration...")
    migrate()
    print("Migration script finished.")
