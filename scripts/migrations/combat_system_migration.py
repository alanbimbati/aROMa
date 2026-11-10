"""
Script to apply schema changes for combat system
"""
import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))

from database import Database, Base
from sqlalchemy import text

def migrate_db():
    db = Database()
    engine = db.engine
    session = db.get_session()
    
    print("🔄 Starting DB Migration for Combat System...")
    
    # 1. Add columns to 'livello'
    columns_to_add = [
        ("elemental_type", "VARCHAR(50) DEFAULT 'Normal'"),
        ("crit_chance", "INTEGER DEFAULT 5"),
        ("crit_multiplier", "FLOAT DEFAULT 1.5"),
        ("required_character_id", "INTEGER DEFAULT NULL")
    ]
    
    for col_name, col_def in columns_to_add:
        try:
            session.execute(text(f"SELECT {col_name} FROM livello LIMIT 1"))  # nosec B608
            print(f"   ✓ Column '{col_name}' already exists.")
        except Exception:
            print(f"   + Adding column '{col_name}'...")
            try:
                session.rollback()
                session.execute(text(f"ALTER TABLE livello ADD COLUMN {col_name} {col_def}"))  # nosec B608
                session.commit()
            except Exception as e:
                print(f"   ❌ Error adding {col_name}: {e}")
                session.rollback()

    # 2. Create 'character_ability' table
    # Using SQLAlchemy create_all is safer for new tables
    try:
        from models.system import CharacterAbility
        Base.metadata.create_all(engine)
        print("   ✓ Table 'character_ability' checked/created.")
    except Exception as e:
        print(f"   ❌ Error creating table: {e}")

    session.close()
    print("✅ Migration complete.")

if __name__ == "__main__":
    migrate_db()
