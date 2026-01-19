import sqlite3
import os

DB_PATH = 'points_dietpi.db'

def migrate_db():
    if not os.path.exists(DB_PATH):
        print(f"Database {DB_PATH} not found!")
        return

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    print(f"Migrating {DB_PATH}...")
    
    # 1. Add columns to utente table
    try:
        cursor.execute("ALTER TABLE utente ADD COLUMN resting_since DATETIME")
        print("Added resting_since to utente")
    except sqlite3.OperationalError as e:
        print(f"resting_since already exists or error: {e}")
        
    try:
        cursor.execute("ALTER TABLE utente ADD COLUMN vigore_until DATETIME")
        print("Added vigore_until to utente")
    except sqlite3.OperationalError as e:
        print(f"vigore_until already exists or error: {e}")

    # 2. Add columns to guilds table
    try:
        cursor.execute("ALTER TABLE guilds ADD COLUMN bordello_level INTEGER DEFAULT 0")
        print("Added bordello_level to guilds")
    except sqlite3.OperationalError as e:
        print(f"bordello_level already exists or error: {e}")
        
    conn.commit()
    conn.close()
    print("Migration complete.")

if __name__ == "__main__":
    migrate_db()
