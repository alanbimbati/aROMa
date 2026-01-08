"""
Migration: Create character_ownership table and add max_concurrent_owners to livello
"""
from database import Database
from sqlalchemy import text

def migrate():
    db = Database()
    session = db.get_session()
    
    try:
        # Create character_ownership table
        session.execute(text("""
            CREATE TABLE IF NOT EXISTS character_ownership (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                character_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                equipped_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                last_change_date DATE,
                UNIQUE(user_id)
            )
        """))
        print("✅ character_ownership table created/verified")
        
        # Add max_concurrent_owners to livello table
        result = session.execute(text("PRAGMA table_info(livello)"))
        columns = [row[1] for row in result]
        
        if 'max_concurrent_owners' not in columns:
            print("Adding max_concurrent_owners column to livello...")
            session.execute(text("ALTER TABLE livello ADD COLUMN max_concurrent_owners INTEGER DEFAULT 1"))
            print("✅ max_concurrent_owners column added")
        else:
            print("⏭️  max_concurrent_owners column already exists")
        
        # Add is_pokemon to livello table
        result = session.execute(text("PRAGMA table_info(livello)"))
        columns = [row[1] for row in result]
        
        if 'is_pokemon' not in columns:
            print("Adding is_pokemon column to livello...")
            session.execute(text("ALTER TABLE livello ADD COLUMN is_pokemon INTEGER DEFAULT 0"))
            print("✅ is_pokemon column added")
        else:
            print("⏭️  is_pokemon column already exists")
        
        session.commit()
        print("\n✅ Migration completed successfully!")
    
    except Exception as e:
        print(f"❌ Migration failed: {e}")
        import traceback
        traceback.print_exc()
        session.rollback()
    finally:
        session.close()

if __name__ == "__main__":
    print("Starting character ownership migration...")
    migrate()
