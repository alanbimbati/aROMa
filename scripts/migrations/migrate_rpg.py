import sqlite3
import datetime

def migrate():
    conn = sqlite3.connect('points.db')
    cursor = conn.cursor()
    
    print("Starting RPG migration...")
    
    # Add new columns to utente table
    columns = [
        ("health", "INTEGER DEFAULT 100"),
        ("max_health", "INTEGER DEFAULT 100"),
        ("mana", "INTEGER DEFAULT 50"),
        ("max_mana", "INTEGER DEFAULT 50"),
        ("base_damage", "INTEGER DEFAULT 10"),
        ("stat_points", "INTEGER DEFAULT 0"),
        ("last_health_restore", "TIMESTAMP"),
        ("allocated_health", "INTEGER DEFAULT 0"),
        ("allocated_mana", "INTEGER DEFAULT 0"),
        ("allocated_damage", "INTEGER DEFAULT 0"),
    ]
    
    for col_name, col_type in columns:
        try:
            cursor.execute(f"ALTER TABLE utente ADD COLUMN {col_name} {col_type}")
            print(f"✓ Added {col_name} to utente")
        except sqlite3.OperationalError as e:
            if "duplicate column" in str(e).lower():
                print(f"  {col_name} already exists")
            else:
                print(f"✗ Error adding {col_name}: {e}")
    
    # Migrate vita -> health (if vita exists and health is null)
    try:
        cursor.execute("UPDATE utente SET health = vita WHERE health IS NULL OR health = 0")
        cursor.execute("UPDATE utente SET max_health = 100 WHERE max_health IS NULL OR max_health = 0")
        print("✓ Migrated vita to health")
    except Exception as e:
        print(f"  Vita migration: {e}")
    
    # Add new columns to livello (character) table
    char_columns = [
        ("special_attack_name", "TEXT"),
        ("special_attack_damage", "INTEGER DEFAULT 0"),
        ("special_attack_mana_cost", "INTEGER DEFAULT 0"),
        ("price", "INTEGER DEFAULT 0"),
        ("image_path", "TEXT"),
        ("description", "TEXT"),
    ]
    
    for col_name, col_type in char_columns:
        try:
            cursor.execute(f"ALTER TABLE livello ADD COLUMN {col_name} {col_type}")
            print(f"✓ Added {col_name} to livello")
        except sqlite3.OperationalError as e:
            if "duplicate column" in str(e).lower():
                print(f"  {col_name} already exists")
            else:
                print(f"✗ Error adding {col_name}: {e}")
    
    # Add new columns to mob table
    mob_columns = [
        ("image_path", "TEXT"),
        ("attack_type", "TEXT DEFAULT 'physical'"),
        ("attack_damage", "INTEGER DEFAULT 10"),
        ("difficulty_tier", "INTEGER DEFAULT 1"),
    ]
    
    for col_name, col_type in mob_columns:
        try:
            cursor.execute(f"ALTER TABLE mob ADD COLUMN {col_name} {col_type}")
            print(f"✓ Added {col_name} to mob")
        except sqlite3.OperationalError as e:
            if "duplicate column" in str(e).lower():
                print(f"  {col_name} already exists")
            else:
                print(f"✗ Error adding {col_name}: {e}")
    
    # Add new columns to raid table
    raid_columns = [
        ("image_path", "TEXT"),
        ("attack_type", "TEXT DEFAULT 'special'"),
        ("attack_damage", "INTEGER DEFAULT 50"),
        ("description", "TEXT"),
    ]
    
    for col_name, col_type in raid_columns:
        try:
            cursor.execute(f"ALTER TABLE raid ADD COLUMN {col_name} {col_type}")
            print(f"✓ Added {col_name} to raid")
        except sqlite3.OperationalError as e:
            if "duplicate column" in str(e).lower():
                print(f"  {col_name} already exists")
            else:
                print(f"✗ Error adding {col_name}: {e}")
    
    conn.commit()
    conn.close()
    print("\n✅ RPG migration completed!")

if __name__ == "__main__":
    migrate()
