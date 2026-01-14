#!/usr/bin/env python3
"""
Migration: Add chat_exp column to utente table
"""
import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(__file__), '..', '..', 'points.db')

def migrate():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    try:
        # Add chat_exp column
        cursor.execute("ALTER TABLE utente ADD COLUMN chat_exp INTEGER DEFAULT 0")
        conn.commit()
        print("✅ Migration completed: Added chat_exp column to utente table")
        
    except sqlite3.OperationalError as e:
        if "duplicate column name" in str(e).lower():
            print("⚠️  Column chat_exp already exists, skipping migration")
        else:
            print(f"❌ Migration failed: {e}")
            conn.rollback()
    except sqlite3.Error as e:
        print(f"❌ Migration failed: {e}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == "__main__":
    migrate()
