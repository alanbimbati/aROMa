import sqlite3
import os

def migrate():
    db_path = 'points.db'
    if not os.path.exists(db_path):
        print(f"Database {db_path} not found.")
        return

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    try:
        # Create dungeon table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS dungeon (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                chat_id INTEGER NOT NULL,
                current_stage INTEGER DEFAULT 0,
                total_stages INTEGER DEFAULT 5,
                status TEXT DEFAULT 'registration',
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                completed_at DATETIME
            )
        """)
        print("Successfully created dungeon table.")
        
        # Create dungeon_participant table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS dungeon_participant (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                dungeon_id INTEGER,
                user_id INTEGER NOT NULL,
                FOREIGN KEY (dungeon_id) REFERENCES dungeon (id)
            )
        """)
        print("Successfully created dungeon_participant table.")

        # Add dungeon_id column to mob table
        try:
            cursor.execute("ALTER TABLE mob ADD COLUMN dungeon_id INTEGER REFERENCES dungeon(id)")
            print("Successfully added dungeon_id column to mob table.")
        except sqlite3.OperationalError as e:
            if "duplicate column name" in str(e).lower():
                print("Column dungeon_id already exists in mob table.")
            else:
                print(f"Error adding column: {e}")

    except Exception as e:
        print(f"Migration error: {e}")

    conn.commit()
    conn.close()

if __name__ == "__main__":
    migrate()
