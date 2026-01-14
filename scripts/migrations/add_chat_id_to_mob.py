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
        # Add chat_id column to mob table
        cursor.execute("ALTER TABLE mob ADD COLUMN chat_id INTEGER")
        print("Successfully added chat_id column to mob table.")
    except sqlite3.OperationalError as e:
        if "duplicate column name" in str(e).lower():
            print("Column chat_id already exists in mob table.")
        else:
            print(f"Error adding column: {e}")

    conn.commit()
    conn.close()

if __name__ == "__main__":
    migrate()
