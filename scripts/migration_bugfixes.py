import sqlite3
import os

DB_PATH = 'points.db'

def migrate():
    print(f"Migrating database at {DB_PATH}...")
    
    if not os.path.exists(DB_PATH):
        print("Database not found!")
        return

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    try:
        # 1. Create season_claimed_reward table
        print("Creating season_claimed_reward table...")
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS season_claimed_reward (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            season_id INTEGER,
            reward_id INTEGER,
            claimed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(season_id) REFERENCES season(id),
            FOREIGN KEY(reward_id) REFERENCES season_reward(id)
        )
        """)
        
        # 2. Add last_message_id to mob table
        print("Checking mob table for last_message_id...")
        cursor.execute("PRAGMA table_info(mob)")
        columns = [info[1] for info in cursor.fetchall()]
        
        if 'last_message_id' not in columns:
            print("Adding last_message_id to mob table...")
            cursor.execute("ALTER TABLE mob ADD COLUMN last_message_id INTEGER")
        else:
            print("last_message_id already exists.")

        conn.commit()
        print("Migration completed successfully!")
        
    except Exception as e:
        print(f"Error during migration: {e}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == "__main__":
    migrate()
