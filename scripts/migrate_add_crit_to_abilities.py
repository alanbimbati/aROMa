"""
Migration script to add crit_chance and crit_multiplier columns to character_ability table
"""
import sqlite3

def migrate():
    conn = sqlite3.connect('points.db')
    cursor = conn.cursor()
    
    # Check if columns already exist
    cursor.execute("PRAGMA table_info(character_ability)")
    columns = [col[1] for col in cursor.fetchall()]
    
    if 'crit_chance' not in columns:
        print("Adding crit_chance column...")
        cursor.execute("ALTER TABLE character_ability ADD COLUMN crit_chance INTEGER DEFAULT 5")
        print("✓ Added crit_chance column")
    else:
        print("crit_chance column already exists")
    
    if 'crit_multiplier' not in columns:
        print("Adding crit_multiplier column...")
        cursor.execute("ALTER TABLE character_ability ADD COLUMN crit_multiplier REAL DEFAULT 1.5")
        print("✓ Added crit_multiplier column")
    else:
        print("crit_multiplier column already exists")
    
    conn.commit()
    conn.close()
    print("\n✅ Migration completed successfully!")

if __name__ == "__main__":
    migrate()
