"""
Database migration script to add achievement system and enhanced combat features.

Run this script to add:
- New tables: achievement, user_achievement, game_event, mob_ability, combat_participation
- New columns to utente: active_status_effects, current_mana
- New columns to mob: passive_abilities, active_abilities, ai_behavior, phase_thresholds, current_phase, active_buffs
"""

from sqlalchemy import create_engine, text
from database import Base
import os

# Import all models to ensure they're registered
from models.user import Utente, Admin
from models.pve import Mob, Raid, RaidParticipation
from models.achievements import Achievement, UserAchievement, GameEvent
from models.combat import MobAbility, CombatParticipation
from models.system import Livello, CharacterAbility, CharacterTransformation, UserTransformation, Domenica, UserCharacter

def backup_database(db_path='points.db'):
    """Create a backup of the database before migration"""
    import shutil
    from datetime import datetime
    
    if os.path.exists(db_path):
        backup_path = f"points_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db"
        shutil.copy2(db_path, backup_path)
        print(f"✅ Database backed up to: {backup_path}")
        return backup_path
    else:
        print(f"⚠️  Database {db_path} not found, skipping backup")
        return None

def add_columns_to_existing_tables(engine):
    """Add new columns to existing tables"""
    
    with engine.connect() as conn:
        print("\n📝 Adding new columns to existing tables...")
        
        # Add to Utente table
        try:
            conn.execute(text("ALTER TABLE utente ADD COLUMN active_status_effects TEXT"))
            print("  ✅ Added active_status_effects to utente")
        except Exception as e:
            print(f"  ⚠️  active_status_effects already exists or error: {e}")
        
        try:
            conn.execute(text("ALTER TABLE utente ADD COLUMN current_mana INTEGER DEFAULT 50"))
            print("  ✅ Added current_mana to utente")
        except Exception as e:
            print(f"  ⚠️  current_mana already exists or error: {e}")
        
        # Add to Mob table
        try:
            conn.execute(text("ALTER TABLE mob ADD COLUMN passive_abilities TEXT"))
            print("  ✅ Added passive_abilities to mob")
        except Exception as e:
            print(f"  ⚠️  passive_abilities already exists or error: {e}")
        
        try:
            conn.execute(text("ALTER TABLE mob ADD COLUMN active_abilities TEXT"))
            print("  ✅ Added active_abilities to mob")
        except Exception as e:
            print(f"  ⚠️  active_abilities already exists or error: {e}")
        
        try:
            conn.execute(text("ALTER TABLE mob ADD COLUMN ai_behavior TEXT DEFAULT 'aggressive'"))
            print("  ✅ Added ai_behavior to mob")
        except Exception as e:
            print(f"  ⚠️  ai_behavior already exists or error: {e}")
        
        try:
            conn.execute(text("ALTER TABLE mob ADD COLUMN phase_thresholds TEXT"))
            print("  ✅ Added phase_thresholds to mob")
        except Exception as e:
            print(f"  ⚠️  phase_thresholds already exists or error: {e}")
        
        try:
            conn.execute(text("ALTER TABLE mob ADD COLUMN current_phase INTEGER DEFAULT 1"))
            print("  ✅ Added current_phase to mob")
        except Exception as e:
            print(f"  ⚠️  current_phase already exists or error: {e}")
        
        try:
            conn.execute(text("ALTER TABLE mob ADD COLUMN active_buffs TEXT"))
            print("  ✅ Added active_buffs to mob")
        except Exception as e:
            print(f"  ⚠️  active_buffs already exists or error: {e}")
        
        conn.commit()

def create_new_tables(engine):
    """Create new tables"""
    print("\n📝 Creating new tables...")
    Base.metadata.create_all(engine)
    print("  ✅ All new tables created")

def migrate():
    """Run the complete migration"""
    print("🚀 Starting aROMaBot Achievement System Migration\n")
    print("=" * 60)
    
    # Backup database
    backup_path = backup_database()
    
    # Create engine
    engine = create_engine('sqlite:///points.db')
    
    # Add columns to existing tables
    add_columns_to_existing_tables(engine)
    
    # Create new tables
    create_new_tables(engine)
    
    print("\n" + "=" * 60)
    print("✅ Migration completed successfully!")
    print("\nNew tables created:")
    print("  - achievement")
    print("  - user_achievement")
    print("  - game_event")
    print("  - mob_ability")
    print("  - combat_participation")
    print("\nNew columns added:")
    print("  - utente: active_status_effects, current_mana")
    print("  - mob: passive_abilities, active_abilities, ai_behavior, phase_thresholds, current_phase, active_buffs")
    
    if backup_path:
        print(f"\n💾 Backup saved at: {backup_path}")
    
    print("\n🎯 Next steps:")
    print("  1. Run seed_achievements.py to populate achievements")
    print("  2. Run seed_mob_abilities.py to populate mob abilities")
    print("  3. Test the new features!")

if __name__ == "__main__":
    migrate()
