#!/usr/bin/env python3
"""
Migration: Add daily_wumpa_earned and last_wumpa_reset columns to utente table
"""
import sqlite3
import os
import datetime

DB_PATH = os.path.join(os.path.dirname(__file__), '..', '..', 'points.db')

def migrate():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    try:
        # Add daily_wumpa_earned column
        try:
            cursor.execute("ALTER TABLE utente ADD COLUMN daily_wumpa_earned INTEGER DEFAULT 0")
            print("✅ Added daily_wumpa_earned column")
        except sqlite3.OperationalError as e:
            if "duplicate column name" in str(e).lower():
                print("⚠️  Column daily_wumpa_earned already exists")
            else:
                raise e

        # Add last_wumpa_reset column
        try:
            cursor.execute("ALTER TABLE utente ADD COLUMN last_wumpa_reset TIMESTAMP")
            print("✅ Added last_wumpa_reset column")
        except sqlite3.OperationalError as e:
            if "duplicate column name" in str(e).lower():
                print("⚠️  Column last_wumpa_reset already exists")
            else:
                raise e
                
        conn.commit()
        print("✅ Migration completed successfully")
        
    except Exception as e:
        print(f"❌ Migration failed: {e}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == "__main__":
    migrate()
