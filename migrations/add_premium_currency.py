"""
Migration script to add cristalli_aroma premium currency column to utente table.

Usage:
    python3 migrations/add_premium_currency.py
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import Database
from sqlalchemy import text

def add_premium_currency_column():
    """Add cristalli_aroma column to utente table"""
    db = Database()
    session = db.get_session()
    
    try:
        print("[MIGRATION] Adding cristalli_aroma column to utente table...")
        
        # Check if column already exists
        check_query = text("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name='utente' AND column_name='cristalli_aroma';
        """)
        
        result = session.execute(check_query).fetchone()
        
        if result:
            print("[MIGRATION] Column cristalli_aroma already exists. Skipping.")
            session.close()
            return
        
        # Add the column
        alter_query = text("""
            ALTER TABLE utente 
            ADD COLUMN cristalli_aroma INTEGER NOT NULL DEFAULT 0;
        """)
        
        session.execute(alter_query)
        session.commit()
        
        print("[MIGRATION] ✅ Successfully added cristalli_aroma column!")
        print("[MIGRATION] All existing users have been set to 0 Cristalli aROMa.")
        
    except Exception as e:
        print(f"[MIGRATION] ❌ Error: {e}")
        session.rollback()
        raise
    finally:
        session.close()

if __name__ == "__main__":
    add_premium_currency_column()
    print("[MIGRATION] Migration complete!")
