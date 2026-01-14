import sqlite3
import os
import json

DB_PATH = os.path.join(os.path.dirname(__file__), '..', '..', 'points.db')

def migrate():
    print(f"Migrating database at {DB_PATH}...")
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    try:
        # 1. Create UserStat table
        print("Creating user_stat table...")
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS user_stat (
                user_id INTEGER NOT NULL,
                stat_key VARCHAR(50) NOT NULL,
                value REAL DEFAULT 0.0,
                last_updated DATETIME DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (user_id, stat_key)
            )
        """)
        
        # 2. Recreate GameEvent table
        print("Recreating game_event table...")
        # Backup old table
        cursor.execute("ALTER TABLE game_event RENAME TO game_event_old")
        
        cursor.execute("""
            CREATE TABLE game_event (
                id INTEGER PRIMARY KEY,
                user_id INTEGER NOT NULL,
                event_type VARCHAR(50) NOT NULL,
                value REAL DEFAULT 0.0,
                context TEXT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                processed BOOLEAN DEFAULT FALSE
            )
        """)
        
        # 3. Recreate Achievement table
        print("Recreating achievement table...")
        cursor.execute("ALTER TABLE achievement RENAME TO achievement_old")
        
        cursor.execute("""
            CREATE TABLE achievement (
                id INTEGER PRIMARY KEY,
                achievement_key VARCHAR(50) UNIQUE NOT NULL,
                name VARCHAR(100) NOT NULL,
                description TEXT NOT NULL,
                stat_key VARCHAR(50) NOT NULL,
                condition_type VARCHAR(20) DEFAULT '>=',
                tiers TEXT NOT NULL,
                category VARCHAR(20),
                icon VARCHAR(255),
                hidden BOOLEAN DEFAULT FALSE,
                flavor_text TEXT
            )
        """)
        
        # 4. Recreate UserAchievement table
        print("Recreating user_achievement table...")
        cursor.execute("ALTER TABLE user_achievement RENAME TO user_achievement_old")
        
        cursor.execute("""
            CREATE TABLE user_achievement (
                user_id INTEGER NOT NULL,
                achievement_key VARCHAR(50) NOT NULL,
                current_tier VARCHAR(20),
                progress_value REAL DEFAULT 0.0,
                unlocked_at DATETIME,
                last_progress_update DATETIME DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (user_id, achievement_key)
            )
        """)
        
        conn.commit()
        print("Migration completed successfully!")
        
    except Exception as e:
        print(f"Migration failed: {e}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == "__main__":
    migrate()
