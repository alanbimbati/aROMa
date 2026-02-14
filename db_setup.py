from database import Database, Base
import os
import importlib
from sqlalchemy import text, inspect
from models.user import Utente
from services.user_service import UserService

def migrate_refinery(db):
    engine = db.engine
    print(f"Checking refinery tables for missing columns and constraints...")
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
            
            # Ensure user_refined_materials exists
            session.execute(text("""
                CREATE TABLE IF NOT EXISTS user_refined_materials (
                    id SERIAL PRIMARY KEY,
                    user_id BIGINT NOT NULL REFERENCES utente(id_Telegram),
                    material_id INTEGER NOT NULL REFERENCES refined_materials(id),
                    quantity INTEGER DEFAULT 0
                );
            """))
            session.commit()

            # Ensure unique constraint on user_refined_materials(user_id, material_id)
            # This is CRITICAL for UPSERT (ON CONFLICT)
            constraints = inspector.get_unique_constraints('user_refined_materials')
            has_uix = any(c['name'] == 'uix_user_material' or set(c['column_names']) == {'user_id', 'material_id'} for c in constraints)
            
            if not has_uix:
                print("Adding missing unique constraint uix_user_material to user_refined_materials...")
                session.execute(text("""
                    ALTER TABLE user_refined_materials 
                    ADD CONSTRAINT uix_user_material UNIQUE (user_id, material_id);
                """))
                session.commit()

            # Ensure refinery_daily exists and has unique constraint on date
            session.execute(text("""
                CREATE TABLE IF NOT EXISTS refinery_daily (
                    id SERIAL PRIMARY KEY,
                    date TIMESTAMP DEFAULT NOW(),
                    resource_id INTEGER NOT NULL REFERENCES resources(id)
                );
            """))
            session.commit()
            
            constraints_daily = inspector.get_unique_constraints('refinery_daily')
            has_date_uix = any(set(c['column_names']) == {'date'} for c in constraints_daily)
            if not has_date_uix:
                print("Adding missing unique constraint to refinery_daily(date)...")
                try:
                    session.execute(text("ALTER TABLE refinery_daily ADD UNIQUE (date)"))
                    session.commit()
                except Exception as e:
                    session.rollback()
                    print(f"Note: Could not add unique constraint to refinery_daily (might already exist without name): {e}")

        except Exception as e:
            session.rollback()
            print(f"Error during refinery schema verification: {e}")
        finally:
            session.close()

        # 1. Update refinery_queue columns
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

def migrate_alchemy_system(db):
    """Create alchemy queue table"""
    session = db.get_session()
    try:
        print("Checking alchemy system tables...")
        inspector = inspect(db.engine)
        existing_table_names = inspector.get_table_names()
        
        if 'alchemy_queue' not in existing_table_names:
            print("Creating alchemy_queue table...")
            session.execute(text("""
                CREATE TABLE alchemy_queue (
                    id SERIAL PRIMARY KEY,
                    user_id BIGINT NOT NULL REFERENCES utente(id_Telegram),
                    potion_name VARCHAR(100) NOT NULL,
                    start_time TIMESTAMP NOT NULL DEFAULT NOW(),
                    completion_time TIMESTAMP NOT NULL,
                    status VARCHAR(20) NOT NULL DEFAULT 'in_progress',
                    xp_gain INTEGER DEFAULT 0
                );
                CREATE INDEX idx_alchemy_user ON alchemy_queue(user_id, status);
            """))
            print("✅ alchemy_queue table created")
        session.commit()
    except Exception as e:
        session.rollback()
        print(f"Error migrating alchemy system: {e}")
    finally:
        session.close()

def migrate_guild_facilities(db):
    """Add laboratory and garden levels to guilds table"""
    session = db.get_session()
    try:
        print("Checking guild facilities columns...")
        inspector = inspect(db.engine)
        columns = [col['name'] for col in inspector.get_columns('guilds')]
        
        if 'laboratory_level' not in columns:
            print("Adding laboratory_level to guilds...")
            session.execute(text("ALTER TABLE guilds ADD COLUMN laboratory_level INTEGER DEFAULT 1"))
        
        if 'garden_level' not in columns:
            print("Adding garden_level to guilds...")
            session.execute(text("ALTER TABLE guilds ADD COLUMN garden_level INTEGER DEFAULT 1"))
            
        session.commit()
        print("✅ Guild facilities columns verified!")
    except Exception as e:
        session.rollback()
        print(f"Error migrating guild facilities: {e}")
    finally:
        session.close()

def migrate_guild_upgrades_v2(db):
    """Add new themed upgrades and customization columns to guilds table"""
    session = db.get_session()
    try:
        print("Checking new guild upgrade columns...")
        inspector = inspect(db.engine)
        columns = [col['name'] for col in inspector.get_columns('guilds')]
        
        new_cols = {
            'dragon_stables_level': 'INTEGER DEFAULT 0',
            'ancient_temple_level': 'INTEGER DEFAULT 0',
            'magic_library_level': 'INTEGER DEFAULT 0',
            'inn_image': 'VARCHAR(255)',
            'bordello_image': 'VARCHAR(255)',
            'laboratory_image': 'VARCHAR(255)',
            'garden_image': 'VARCHAR(255)'
        }
        
        missing = []
        for col_name, col_type in new_cols.items():
            if col_name not in columns:
                missing.append(f"ALTER TABLE guilds ADD COLUMN {col_name} {col_type}")
        
        if missing:
            print(f"Adding {len(missing)} new columns to guilds...")
            for sql in missing:
                session.execute(text(sql))
            session.commit()
            print("✅ Guild upgrade columns added!")
        else:
            print("✅ Guild upgrade columns already exist.")
            
    except Exception as e:
        session.rollback()
        print(f"Error migrating guild upgrades v2: {e}")
    finally:
        session.close()

def migrate_cultivation_system(db):
    """Create garden_slots table if not exists"""
    session = db.get_session()
    try:
        print("Checking cultivation tables...")
        inspector = inspect(db.engine)
        tables = inspector.get_table_names()
        
        if 'garden_slots' not in tables:
            print("Creating garden_slots table...")
            # We use SQLAlchemy create_all for new tables efficiently
            from models.cultivation import GardenSlot
            GardenSlot.__table__.create(db.engine)
            print("✅ garden_slots table created!")
        else:
            # Check for missing columns in existing table
            columns = [col['name'] for col in inspector.get_columns('garden_slots')]
            missing = []
            if 'moisture' not in columns:
                missing.append("ALTER TABLE garden_slots ADD COLUMN moisture INTEGER DEFAULT 100")
            if 'last_watered_at' not in columns:
                missing.append("ALTER TABLE garden_slots ADD COLUMN last_watered_at TIMESTAMP")
            if 'rot_time' not in columns:
                missing.append("ALTER TABLE garden_slots ADD COLUMN rot_time TIMESTAMP")
            
            if missing:
                print(f"Adding {len(missing)} missing columns to garden_slots...")
                for sql in missing:
                    session.execute(text(sql))
                session.commit()
                print("✅ Garden columns added successfully!")
            
    except Exception as e:
        session.rollback()
        print(f"Error migrating cultivation system: {e}")
    finally:
        session.close()

def migrate_user_table(db):
    """Add missing columns to utente table"""
    session = db.get_session()
    try:
        print("Checking utente table for missing columns...")
        inspector = inspect(db.engine)
        columns = [col['name'] for col in inspector.get_columns('utente')]
        
        if 'profumino_until' not in columns:
            print("Adding profumino_until to utente...")
            session.execute(text("ALTER TABLE utente ADD COLUMN profumino_until TIMESTAMP WITHOUT TIME ZONE"))
            
        session.commit()
    except Exception as e:
        session.rollback()
        print(f"Error migrating utente table: {e}")
    finally:
        session.close()

def migrate_mob_tactical(db):
    """Add mana and defense columns to mob table"""
    session = db.get_session()
    try:
        print("Checking mob table for tactical columns...")
        
        # Check existing columns using information_schema directly (no locks)
        existing_cols = session.execute(text("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = 'mob'
        """)).fetchall()
        existing_cols = [row[0] for row in existing_cols]
        
        missing = []
        if 'mana' not in existing_cols:
            missing.append("ALTER TABLE mob ADD COLUMN mana INTEGER DEFAULT 0")
        if 'max_mana' not in existing_cols:
            missing.append("ALTER TABLE mob ADD COLUMN max_mana INTEGER DEFAULT 0")
        if 'is_defending' not in existing_cols:
            missing.append("ALTER TABLE mob ADD COLUMN is_defending BOOLEAN DEFAULT FALSE")
            
        if missing:
            print(f"Adding {len(missing)} tactical columns to mob table...")
            # Set timeout to avoid hanging indefinitely if table is locked
            try:
                session.execute(text("SET lock_timeout = '5s'"))
            except Exception as e:
                print(f"Could not set lock_timeout (might not be supported): {e}")

            for sql in missing:
                try:
                    session.execute(text(sql))
                    print(f"Executed: {sql}")
                except Exception as e:
                    print(f"⚠️ Failed to execute {sql}: {e}")
                    session.rollback()
            session.commit()
            print("✅ Mob tactical columns check complete!")
        else:
            print("✅ Mob tactical columns already exist.")
            
    except Exception as e:
        session.rollback()
        print(f"Error migrating mob table: {e}")
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
            {'id': 3, 'name': 'Diamante', 'rarity': 3},
            
            # Alchemy Materials
            {'id': 4, 'name': 'Frammenti Alchemici', 'rarity': 1},
            {'id': 5, 'name': 'Estratto Puro', 'rarity': 2},
            {'id': 6, 'name': 'Elisir Primordiale', 'rarity': 3},
            
            # Garden Materials
            {'id': 7, 'name': 'Compost Organico', 'rarity': 1},
            {'id': 8, 'name': 'Concime Arricchito', 'rarity': 2},
            {'id': 9, 'name': 'Essenza Botanica', 'rarity': 3}
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
                                          crafting_time, crafting_requirements, description, set_name, effect_type)
                    VALUES (:id, :name, :slot, :rarity, :min_level, :stats_json, 
                            :crafting_time, :crafting_requirements, :description, :set_name, :effect_type)
                    ON CONFLICT (id) DO UPDATE SET
                        name = EXCLUDED.name, slot = EXCLUDED.slot, rarity = EXCLUDED.rarity,
                        min_level = EXCLUDED.min_level, stats_json = EXCLUDED.stats_json,
                        crafting_time = EXCLUDED.crafting_time, 
                        crafting_requirements = EXCLUDED.crafting_requirements,
                        description = EXCLUDED.description, set_name = EXCLUDED.set_name,
                        effect_type = EXCLUDED.effect_type
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
                    'set_name': row.get('set_name', ''),
                    'effect_type': row.get('effect_type', None)
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
    # migrate_premium_currency(db) # Definition missing
    migrate_alchemy_system(db)
    migrate_guild_facilities(db)
    migrate_guild_upgrades_v2(db)
    migrate_cultivation_system(db)
    migrate_user_table(db)
    migrate_mob_tactical(db)
    migrate_recalculate_stats(db)
    
    # 3. Seeding (Idempotent ON CONFLICT)
    print("🌱 Seeding essential data...")
    seed_refined_materials(db)
    seed_resources(db)
    seed_equipment(db)
    
    print("\n✨ Database setup complete and verified! ✨")

if __name__ == "__main__":
    init_database()
