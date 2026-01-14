#!/usr/bin/env python3
"""
Migration: Fix stat points for existing users (should be 2 per level)
"""
import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(__file__), '..', '..', 'points.db')

def migrate():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    try:
        # Get all users and update their stat_points to be 2 per level
        cursor.execute("SELECT id_telegram, livello, stat_points FROM utente")
        users = cursor.fetchall()
        
        updated_count = 0
        for user_id, level, current_points in users:
            # Skip users with NULL level
            if level is None:
                level = 1
            
            # Calculate what stat points should be (2 per level)
            expected_points = level * 2
            
            # Update if different
            if current_points != expected_points:
                cursor.execute(
                    "UPDATE utente SET stat_points = ? WHERE id_telegram = ?",
                    (expected_points, user_id)
                )
                updated_count += 1
                print(f"Updated user {user_id}: Level {level}, {current_points} -> {expected_points} stat points")
        
        conn.commit()
        print(f"✅ Migration completed: Updated {updated_count} users")
        
    except sqlite3.Error as e:
        print(f"❌ Migration failed: {e}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == "__main__":
    migrate()
