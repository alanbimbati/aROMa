from database import Database, Base
import os
import importlib
from sqlalchemy import text, inspect
from models.user import Utente
from services.user_service import UserService

def migrate_refinery(db):
    engine = db.engine
    print(f"Checking refinery_queue table for missing columns...")
    try:
        inspector = inspect(engine)
        
        # 0. Ensure refined_materials exists and is seeded
        session = db.get_session()
        try:
            session.execute(text("""
                CREATE TABLE IF NOT EXISTS refined_materials (
                    id SERIAL PRIMARY KEY,
                    name VARCHAR(100) UNIQUE NOT NULL,
                    rarity INTEGER NOT NULL
                );
            """))
            session.commit()
        except Exception as e:
            session.rollback()
            print(f"Error creating refined_materials: {e}")
        finally:
            session.close()

        columns = [col['name'] for col in inspector.get_columns('refinery_queue')]
        
        missing = []
        if 'result_t1' not in columns:
            missing.append("ALTER TABLE refinery_queue ADD COLUMN result_t1 INTEGER DEFAULT 0")
        if 'result_t2' not in columns:
            missing.append("ALTER TABLE refinery_queue ADD COLUMN result_t2 INTEGER DEFAULT 0")
        if 'result_t3' not in columns:
            missing.append("ALTER TABLE refinery_queue ADD COLUMN result_t3 INTEGER DEFAULT 0")
            
        if missing:
            print(f"Adding {len(missing)} missing columns to refinery_queue...")
            session = db.get_session()
            try:
                for sql in missing:
                    session.execute(text(sql))
                session.commit()
                print("Refinery columns added successfully!")
            except Exception as e:
                session.rollback()
                print(f"Error adding refinery columns: {e}")
            finally:
                session.close()
    except Exception as e:
        print(f"Refinery migration skipped (table might not exist yet): {e}")

def migrate_parry_system(db):
    """Create parry system tables and modify utente table"""
    session = db.get_session()
    try:
        print("Checking parry system tables...")
        inspector = inspect(db.engine)
        existing_table_names = inspector.get_table_names()
        
        # Create parry_states table
        if 'parry_states' not in existing_table_names:
            print("Creating parry_states table...")
            session.execute(text("""
                CREATE TABLE parry_states (
                    id SERIAL PRIMARY KEY,
                    user_id BIGINT NOT NULL,
                    mob_id INTEGER,
                    activated_at TIMESTAMP NOT NULL DEFAULT NOW(),
                    expires_at TIMESTAMP NOT NULL,
                    status VARCHAR(20) NOT NULL DEFAULT 'active',
                    reaction_time_ms INTEGER,
                    counterattack_at TIMESTAMP,
                    created_at TIMESTAMP DEFAULT NOW()
                );
                CREATE INDEX idx_parry_active ON parry_states(user_id, status, expires_at);
                CREATE INDEX idx_parry_user_recent ON parry_states(user_id, created_at DESC);
            """))
            print("✅ parry_states table created")
        
        # Create combat_telemetry table
        if 'combat_telemetry' not in existing_table_names:
            print("Creating combat_telemetry table...")
            session.execute(text("""
                CREATE TABLE combat_telemetry (
                    id SERIAL PRIMARY KEY,
                    user_id BIGINT NOT NULL,
                    event_type VARCHAR(50) NOT NULL,
                    combat_id VARCHAR(100),
                    mob_id INTEGER,
                    mob_level INTEGER,
                    mob_is_boss BOOLEAN DEFAULT FALSE,
                    reaction_time_ms INTEGER,
                    window_duration_ms INTEGER DEFAULT 3000,
                    counterattack_time_ms INTEGER,
                    damage_dealt INTEGER DEFAULT 0,
                    damage_avoided INTEGER DEFAULT 0,
                    cooldown_saved_ms INTEGER DEFAULT 0,
                    user_level INTEGER,
                    user_hp_percent FLOAT,
                    user_mana_used INTEGER DEFAULT 0,
                    metadata JSONB,
                    timestamp TIMESTAMP DEFAULT NOW()
                );
                CREATE INDEX idx_telemetry_user_type ON combat_telemetry(user_id, event_type, timestamp DESC);
                CREATE INDEX idx_telemetry_combat ON combat_telemetry(combat_id, timestamp);
                CREATE INDEX idx_telemetry_event ON combat_telemetry(event_type, timestamp DESC);
            """))
            print("✅ combat_telemetry table created")
        
        # Create parry_stats table
        if 'parry_stats' not in existing_table_names:
            print("Creating parry_stats table...")
            session.execute(text("""
                CREATE TABLE parry_stats (
                    user_id BIGINT PRIMARY KEY,
                    total_parry_attempts INTEGER DEFAULT 0,
                    total_parry_success INTEGER DEFAULT 0,
                    total_parry_perfect INTEGER DEFAULT 0,
                    total_parry_failed INTEGER DEFAULT 0,
                    max_parry_streak INTEGER DEFAULT 0,
                    current_parry_streak INTEGER DEFAULT 0,
                    max_perfect_streak INTEGER DEFAULT 0,
                    current_perfect_streak INTEGER DEFAULT 0,
                    boss_parries INTEGER DEFAULT 0,
                    perfect_boss_parries INTEGER DEFAULT 0,
                    total_damage_avoided BIGINT DEFAULT 0,
                    total_counterattack_damage BIGINT DEFAULT 0,
                    total_counters_in_window INTEGER DEFAULT 0,
                    total_counters_late INTEGER DEFAULT 0,
                    average_reaction_time_ms INTEGER,
                    best_reaction_time_ms INTEGER,
                    average_counter_time_ms INTEGER,
                    flawless_victories INTEGER DEFAULT 0,
                    speed_victories INTEGER DEFAULT 0,
                    last_parry_at TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT NOW()
                );
                CREATE INDEX idx_parry_stats_user ON parry_stats(user_id);
            """))
            print("✅ parry_stats table created")
        
        # Add columns to utente table
        columns = [col['name'] for col in inspector.get_columns('utente')]
        if 'parry_enabled' not in columns:
            session.execute(text("ALTER TABLE utente ADD COLUMN parry_enabled BOOLEAN DEFAULT TRUE"))
            print("✅ Added parry_enabled to utente")
        if 'parry_skill_level' not in columns:
            session.execute(text("ALTER TABLE utente ADD COLUMN parry_skill_level INTEGER DEFAULT 1"))
            print("✅ Added parry_skill_level to utente")
            
        session.commit()
    except Exception as e:
        session.rollback()
        print(f"Error migrating parry system: {e}")
    finally:
        session.close()

def migrate_premium_currency(db):
    """Add cristalli_aroma column to utente table"""
    session = db.get_session()
    try:
        inspector = inspect(db.engine)
        columns = [col['name'] for col in inspector.get_columns('utente')]
        if 'cristalli_aroma' not in columns:
            print("Adding cristalli_aroma column to utente table...")
            session.execute(text("ALTER TABLE utente ADD COLUMN cristalli_aroma INTEGER NOT NULL DEFAULT 0"))
            session.commit()
            print("✅ Successfully added cristalli_aroma column!")
    except Exception as e:
        session.rollback()
        print(f"Error migrating premium currency: {e}")
    finally:
        session.close()

def migrate_recalculate_stats(db):
    """Recalculate stats for all users"""
    session = db.get_session()
    user_service = UserService()
    try:
        users = session.query(Utente).all()
        print(f"Recalculating stats for {len(users)} users...")
        for user in users:
            user_service.recalculate_stats(user.id_telegram, session=session)
        session.commit()
        print("✅ Stats recalculated for all users!")
    except Exception as e:
        session.rollback()
        print(f"Error recalculating stats: {e}")
    finally:
        session.close()

def seed_refined_materials(db):
    print("Seeding refined_materials...")
    session = db.get_session()
    try:
        materials = [
            {'id': 1, 'name': 'Rottami', 'rarity': 1},
            {'id': 2, 'name': 'Materiale Pregiato', 'rarity': 2},
            {'id': 3, 'name': 'Diamante', 'rarity': 3}
        ]
        for mat in materials:
            session.execute(text("""
                INSERT INTO refined_materials (id, name, rarity)
                VALUES (:id, :name, :rarity)
                ON CONFLICT (id) DO UPDATE SET name = EXCLUDED.name, rarity = EXCLUDED.rarity
            """), mat)
        session.commit()
        print("✅ Refined materials seeded!")
    except Exception as e:
        session.rollback()
        print(f"Error seeding refined materials: {e}")
    finally:
        session.close()

def seed_resources(db):
    import csv
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    csv_path = os.path.join(BASE_DIR, 'data', 'resources.csv')
    
    if not os.path.exists(csv_path):
        print(f"⚠️ {csv_path} not found, skipping resource seeding.")
        return

    print("Seeding resources from CSV...")
    session = db.get_session()
    try:
        with open(csv_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                session.execute(text("""
                    INSERT INTO resources (id, name, rarity, drop_source, description, image)
                    VALUES (:id, :name, :rarity, :drop_source, :description, :image)
                    ON CONFLICT (id) DO UPDATE SET
                        name = EXCLUDED.name, rarity = EXCLUDED.rarity,
                        drop_source = EXCLUDED.drop_source, description = EXCLUDED.description,
                        image = EXCLUDED.image
                """), {
                    'id': int(row['id']),
                    'name': row['name'],
                    'rarity': int(row['rarity']),
                    'drop_source': row.get('drop_source', 'mob'),
                    'description': row.get('description', ''),
                    'image': row.get('image', None)
                })
        session.commit()
        print("✅ Resources seeded!")
    except Exception as e:
        session.rollback()
        print(f"Error seeding resources: {e}")
    finally:
        session.close()

def seed_equipment(db):
    import csv
    import json
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    csv_path = os.path.join(BASE_DIR, 'data', 'equipment.csv')
    
    if not os.path.exists(csv_path):
        print(f"⚠️ {csv_path} not found, skipping equipment seeding.")
        return

    print("Seeding equipment from CSV...")
    session = db.get_session()
    try:
        with open(csv_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                session.execute(text("""
                    INSERT INTO equipment (id, name, slot, rarity, min_level, stats_json, 
                                          crafting_time, crafting_requirements, description, set_name)
                    VALUES (:id, :name, :slot, :rarity, :min_level, :stats_json, 
                            :crafting_time, :crafting_requirements, :description, :set_name)
                    ON CONFLICT (id) DO UPDATE SET
                        name = EXCLUDED.name, slot = EXCLUDED.slot, rarity = EXCLUDED.rarity,
                        min_level = EXCLUDED.min_level, stats_json = EXCLUDED.stats_json,
                        crafting_time = EXCLUDED.crafting_time, 
                        crafting_requirements = EXCLUDED.crafting_requirements,
                        description = EXCLUDED.description, set_name = EXCLUDED.set_name
                """), {
                    'id': int(row['id']),
                    'name': row['name'],
                    'slot': row['slot'],
                    'rarity': int(row['rarity']),
                    'min_level': int(row['min_level']),
                    'stats_json': row['stats_json'],
                    'crafting_time': int(row.get('crafting_time', 0)),
                    'crafting_requirements': row.get('crafting_requirements', '{}'),
                    'description': row.get('description', ''),
                    'set_name': row.get('set_name', '')
                })
        session.commit()
        print("✅ Equipment seeded!")
    except Exception as e:
        session.rollback()
        print(f"Error seeding equipment: {e}")
    finally:
        session.close()

import time

def init_database():
    """Robust database initialization with retry logic for production."""
    db = Database()
    engine = db.engine
    
    # Retry logic for DB connection (crucial for Docker/DietPi startup)
    max_retries = 5
    retry_delay = 5 # seconds
    
    print(f"🚀 Initializing database: {engine.url.database} on {engine.name}")
    
    connected = False
    for i in range(max_retries):
        try:
            # Simple connectivity check
            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            connected = True
            break
        except Exception as e:
            print(f"⏳ Waiting for database... attempt {i+1}/{max_retries} (Error: {e})")
            time.sleep(retry_delay)
            
    if not connected:
        print("❌ CRITICAL: Could not connect to database after multiple attempts. Exiting.")
        return

    # Import all models
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    models_dir = os.path.join(BASE_DIR, 'models')
    
    if os.path.exists(models_dir):
        for filename in os.listdir(models_dir):
            if filename.endswith('.py') and filename != '__init__.py':
                module_name = f"models.{filename[:-3]}"
                try:
                    importlib.import_module(module_name)
                except Exception as e:
                    print(f"⚠️ Warning: could not import {module_name}: {e}")
    else:
        print(f"⚠️ Warning: models directory not found at {models_dir}")

    # 1. Create tables (Idempotent)
    try:
        print("🔨 Verifying/Creating tables...")
        Base.metadata.create_all(bind=engine)
        print("✅ Tables verified!")
    except Exception as e:
        print(f"❌ Error during create_all: {e}")

    # 2. Migrations (Internal safety check within each function)
    print("🔄 Running schema migrations...")
    migrate_refinery(db)
    migrate_parry_system(db)
    migrate_premium_currency(db)
    migrate_recalculate_stats(db)
    
    # 3. Seeding (Idempotent ON CONFLICT)
    print("🌱 Seeding essential data...")
    seed_refined_materials(db)
    seed_resources(db)
    seed_equipment(db)
    
    print("\n✨ Database setup complete and verified! ✨")

if __name__ == "__main__":
    init_database()
