"""
Migration: Add combat fields to mob table
"""
from database import Database
from sqlalchemy import text

def migrate():
    db = Database()
    session = db.get_session()
    
    try:
        print("⚔️ Starting combat system migration...")
        
        # Check mob table columns
        result = session.execute(text("PRAGMA table_info(mob)"))
        columns = [row[1] for row in result]
        
        # Add mob_level
        if 'mob_level' not in columns:
            print("Adding mob_level column...")
            session.execute(text("ALTER TABLE mob ADD COLUMN mob_level INTEGER DEFAULT 1"))
        else:
            print("⏭️  mob_level already exists")
            
        # Add max_health (check if exists, model says it should but maybe DB is old)
        if 'max_health' not in columns:
            print("Adding max_health column...")
            session.execute(text("ALTER TABLE mob ADD COLUMN max_health INTEGER DEFAULT 100"))
        else:
            print("⏭️  max_health already exists")
            
        # Add health (current health)
        if 'health' not in columns:
            print("Adding health column...")
            session.execute(text("ALTER TABLE mob ADD COLUMN health INTEGER DEFAULT 100"))
        else:
            print("⏭️  health already exists")

        session.commit()
        print("\n✅ Combat migration completed successfully!")
    
    except Exception as e:
        print(f"❌ Migration failed: {e}")
        import traceback
        traceback.print_exc()
        session.rollback()
    finally:
        session.close()

if __name__ == "__main__":
    migrate()
