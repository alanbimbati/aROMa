"""
Migration: Add is_boss and description columns to mob table
Unifies Mob and Raid into a single Mob table
"""
import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))

from database import Database
from sqlalchemy import text

def migrate():
    db = Database()
    session = db.get_session()
    
    try:
        print("🔄 Starting migration for Mob/Raid unification...")
        
        # Check existing columns
        result = session.execute(text("PRAGMA table_info(mob)"))
        columns = [row[1] for row in result]
        
        # Add is_boss column
        if 'is_boss' not in columns:
            print("Adding is_boss column to mob...")
            session.execute(text("ALTER TABLE mob ADD COLUMN is_boss BOOLEAN DEFAULT 0"))
            session.commit()
            print("✅ is_boss column added")
        else:
            print("⏭️  is_boss column already exists")
        
        # Add description column
        if 'description' not in columns:
            print("Adding description column to mob...")
            session.execute(text("ALTER TABLE mob ADD COLUMN description TEXT"))
            session.commit()
            print("✅ description column added")
        else:
            print("⏭️  description column already exists")
        
        # Migrate existing Raid data to Mob (if raid table exists)
        try:
            result = session.execute(text("SELECT name FROM sqlite_master WHERE type='table' AND name='raid'"))
            if result.fetchone():
                print("\n📦 Migrating existing Raid data to Mob...")
                
                # Get all active raids
                raids = session.execute(text("""
                    SELECT id, boss_name, health, max_health, attack_damage, attack_type, description, speed
                    FROM raid 
                    WHERE is_active = 1
                """))
                
                migrated_count = 0
                for raid in raids:
                    raid_id, boss_name, health, max_health, attack_damage, attack_type, description, speed = raid
                    
                    # Create Mob entry with is_boss=True
                    session.execute(text("""
                        INSERT INTO mob (name, health, max_health, attack_damage, attack_type, 
                                       difficulty_tier, speed, is_boss, description, is_dead)
                        VALUES (:name, :health, :max_health, :attack_damage, :attack_type, 
                               5, :speed, 1, :description, 0)
                    """), {
                        'name': boss_name,
                        'health': health,
                        'max_health': max_health,
                        'attack_damage': attack_damage,
                        'attack_type': attack_type or 'special',
                        'speed': speed or 70,
                        'description': description or ''
                    })
                    migrated_count += 1
                
                session.commit()
                print(f"✅ Migrated {migrated_count} active raid(s) to Mob table")
        except Exception as e:
            print(f"⚠️  Could not migrate Raid data (table may not exist): {e}")
            session.rollback()
        
        print("\n✅ Migration completed successfully!")
    
    except Exception as e:
        print(f"❌ Migration failed: {e}")
        import traceback
        traceback.print_exc()
        session.rollback()
    finally:
        session.close()

if __name__ == "__main__":
    print("Starting Mob/Raid unification migration...")
    migrate()

