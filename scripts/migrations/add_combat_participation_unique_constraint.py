#!/usr/bin/env python3
"""
Migration: Add unique constraint to combat_participation table
"""
import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(__file__), '..', '..', 'points.db')

def migrate():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    try:
        # Check if constraint already exists by trying to create it
        # SQLite doesn't have ALTER TABLE ADD CONSTRAINT, so we need to recreate the table
        
        # First, check if we need to migrate
        cursor.execute("PRAGMA table_info(combat_participation)")
        columns = cursor.fetchall()
        
        # Create new table with unique constraint
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS combat_participation_new (
                id INTEGER PRIMARY KEY,
                mob_id INTEGER,
                user_id INTEGER NOT NULL,
                damage_dealt INTEGER DEFAULT 0,
                hits_landed INTEGER DEFAULT 0,
                critical_hits INTEGER DEFAULT 0,
                healing_done INTEGER DEFAULT 0,
                buffs_applied INTEGER DEFAULT 0,
                exp_earned INTEGER DEFAULT 0,
                loot_received TEXT,
                reward_claimed INTEGER DEFAULT 0,
                first_hit_time DATETIME,
                last_hit_time DATETIME,
                FOREIGN KEY (mob_id) REFERENCES mob(id),
                UNIQUE (mob_id, user_id)
            )
        """)
        
        # Copy data from old table, removing duplicates (keep the one with highest damage)
        cursor.execute("""
            INSERT INTO combat_participation_new 
            SELECT * FROM combat_participation
            WHERE id IN (
                SELECT MAX(id) FROM combat_participation 
                GROUP BY mob_id, user_id
            )
        """)
        
        # Drop old table and rename new one
        cursor.execute("DROP TABLE combat_participation")
        cursor.execute("ALTER TABLE combat_participation_new RENAME TO combat_participation")
        
        conn.commit()
        print("✅ Migration completed: Added unique constraint to combat_participation")
        
    except sqlite3.Error as e:
        print(f"❌ Migration failed: {e}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == "__main__":
    migrate()
