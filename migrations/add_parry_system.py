"""
Database Migration: Add Parry System Tables

This migration creates three new tables for the advanced parry system:
1. parry_states: Active parry window tracking
2. combat_telemetry: Event logging for analytics
3. parry_stats: Aggregated user statistics

Also adds parry-related columns to the utente table.

Usage:
    python3 migrations/add_parry_system.py
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import Database
from sqlalchemy import text

def add_parry_system_tables():
    """Create parry system tables and modify utente table"""
    db = Database()
    session = db.get_session()
    
    try:
        print("[MIGRATION] Creating parry system tables...")
        
        # Check if tables already exist
        check_query = text("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public' 
            AND table_name IN ('parry_states', 'combat_telemetry', 'parry_stats');
        """)
        
        existing_tables = session.execute(check_query).fetchall()
        existing_table_names = [row[0] for row in existing_tables]
        
        if len(existing_table_names) == 3:
            print("[MIGRATION] Parry system tables already exist. Skipping.")
            session.close()
            return
        
        # Create parry_states table
        if 'parry_states' not in existing_table_names:
            print("[MIGRATION] Creating parry_states table...")
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
            print("[MIGRATION] ✅ parry_states table created")
        
        # Create combat_telemetry table
        if 'combat_telemetry' not in existing_table_names:
            print("[MIGRATION] Creating combat_telemetry table...")
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
            print("[MIGRATION] ✅ combat_telemetry table created")
        
        # Create parry_stats table
        if 'parry_stats' not in existing_table_names:
            print("[MIGRATION] Creating parry_stats table...")
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
            print("[MIGRATION] ✅ parry_stats table created")
        
        # Add columns to utente table
        print("[MIGRATION] Adding parry columns to utente table...")
        
        # Check if columns already exist
        check_col_query = text("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = 'utente' 
            AND column_name IN ('parry_enabled', 'parry_skill_level');
        """)
        
        existing_cols = session.execute(check_col_query).fetchall()
        existing_col_names = [row[0] for row in existing_cols]
        
        if 'parry_enabled' not in existing_col_names:
            session.execute(text("""
                ALTER TABLE utente ADD COLUMN parry_enabled BOOLEAN DEFAULT TRUE;
            """))
            print("[MIGRATION] ✅ Added parry_enabled column to utente")
        
        if 'parry_skill_level' not in existing_col_names:
            session.execute(text("""
                ALTER TABLE utente ADD COLUMN parry_skill_level INTEGER DEFAULT 1;
            """))
            print("[MIGRATION] ✅ Added parry_skill_level column to utente")
        
        session.commit()
        
        print("\n[MIGRATION] ✅ Parry system migration completed successfully!")
        print("[MIGRATION] Tables created:")
        print("  - parry_states (active parry tracking)")
        print("  - combat_telemetry (event logging)")
        print("  - parry_stats (user statistics)")
        print("[MIGRATION] Columns added to utente:")
        print("  - parry_enabled")
        print("  - parry_skill_level")
        
    except Exception as e:
        print(f"[MIGRATION] ❌ Error: {e}")
        session.rollback()
        raise
    finally:
        session.close()

if __name__ == "__main__":
    add_parry_system_tables()
    print("\n[MIGRATION] Migration complete!")
