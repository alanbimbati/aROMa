import sqlite3

def migrate():
    conn = sqlite3.connect('points.db')
    cursor = conn.cursor()
    
    # Mob table
    try:
        cursor.execute('''CREATE TABLE IF NOT EXISTS mob (
            id INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            health INTEGER NOT NULL,
            max_health INTEGER NOT NULL,
            spawn_time TIMESTAMP,
            is_dead BOOLEAN DEFAULT 0,
            killer_id INTEGER,
            reward_claimed BOOLEAN DEFAULT 0
        )''')
        print("Created mob table")
    except Exception as e:
        print(f"Error creating mob table: {e}")

    # Raid table
    try:
        cursor.execute('''CREATE TABLE IF NOT EXISTS raid (
            id INTEGER PRIMARY KEY,
            boss_name TEXT NOT NULL,
            health INTEGER NOT NULL,
            max_health INTEGER NOT NULL,
            start_time TIMESTAMP,
            end_time TIMESTAMP,
            is_active BOOLEAN DEFAULT 1
        )''')
        print("Created raid table")
    except Exception as e:
        print(f"Error creating raid table: {e}")

    # RaidParticipation table
    try:
        cursor.execute('''CREATE TABLE IF NOT EXISTS raid_participation (
            id INTEGER PRIMARY KEY,
            raid_id INTEGER,
            user_id INTEGER NOT NULL,
            damage_dealt INTEGER DEFAULT 0,
            FOREIGN KEY(raid_id) REFERENCES raid(id)
        )''')
        print("Created raid_participation table")
    except Exception as e:
        print(f"Error creating raid_participation table: {e}")

    conn.commit()
    conn.close()

if __name__ == "__main__":
    migrate()
