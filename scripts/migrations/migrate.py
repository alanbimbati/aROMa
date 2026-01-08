import sqlite3

def migrate():
    conn = sqlite3.connect('points.db')
    cursor = conn.cursor()
    
    try:
        cursor.execute("ALTER TABLE utente ADD COLUMN invincible_until TIMESTAMP")
        print("Added invincible_until column")
    except sqlite3.OperationalError as e:
        print(f"invincible_until might already exist: {e}")

    try:
        cursor.execute("ALTER TABLE utente ADD COLUMN luck_boost INTEGER DEFAULT 0")
        print("Added luck_boost column")
    except sqlite3.OperationalError as e:
        print(f"luck_boost might already exist: {e}")

    conn.commit()
    conn.close()

if __name__ == "__main__":
    migrate()
