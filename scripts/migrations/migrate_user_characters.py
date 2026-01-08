import sqlite3

def migrate():
    conn = sqlite3.connect('points.db')
    cursor = conn.cursor()
    
    print("Creating user_character table...")
    
    try:
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS user_character (
                id INTEGER PRIMARY KEY,
                user_id INTEGER NOT NULL,
                character_id INTEGER NOT NULL,
                obtained_at DATE
            )
        """)
        print("✓ Created user_character table")
    except Exception as e:
        print(f"✗ Error creating table: {e}")
        
    conn.commit()
    conn.close()

if __name__ == "__main__":
    migrate()
