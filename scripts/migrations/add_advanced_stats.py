"""
Migration script to add new stats to the Utente table:
- resistance (INT, default 0)
- crit_chance (INT, default 0)  
- speed (INT, default 0)
- allocated_resistance (INT, default 0)
- allocated_crit (INT, default 0)
- allocated_speed (INT, default 0)
"""

import sqlite3
import os
import shutil
from datetime import datetime

DB_NAME = "points.db"

def backup_db():
    """Create a backup of the database"""
    if not os.path.exists(DB_NAME):
        print(f"Database {DB_NAME} not found!")
        return False
    
    backup_name = f"{DB_NAME}.backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    shutil.copy2(DB_NAME, backup_name)
    print(f"✅ Backup created: {backup_name}")
    return True

def add_column(cursor, table, column, col_type):
    """Add a column to a table if it doesn't exist"""
    try:
        cursor.execute(f"ALTER TABLE {table} ADD COLUMN {column} {col_type}")
        print(f"✅ Added column {column} to {table}")
    except sqlite3.OperationalError as e:
        if "duplicate column name" in str(e):
            print(f"⚠️  Column {column} already exists in {table}")
        else:
            print(f"❌ Error adding column {column} to {table}: {e}")

def migrate():
    """Run the migration"""
    if not backup_db():
        return
    
    print(f"\nStarting migration of {DB_NAME}...\n")
    
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    try:
        # Add new stat columns
        print("Adding stat columns...")
        add_column(cursor, "utente", "resistance", "INTEGER DEFAULT 0")
        add_column(cursor, "utente", "crit_chance", "INTEGER DEFAULT 0")
        add_column(cursor, "utente", "speed", "INTEGER DEFAULT 0")
        
        # Add allocated stat columns
        print("\nAdding allocated stat columns...")
        add_column(cursor, "utente", "allocated_resistance", "INTEGER DEFAULT 0")
        add_column(cursor, "utente", "allocated_crit", "INTEGER DEFAULT 0")
        add_column(cursor, "utente", "allocated_speed", "INTEGER DEFAULT 0")
        
        conn.commit()
        print("\n✅ Migration completed successfully!")
        
    except Exception as e:
        conn.rollback()
        print(f"\n❌ Migration failed: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    migrate()
