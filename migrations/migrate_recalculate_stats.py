"""
Database Migration: Recalculate All User Stats

Ensures the correct speed formula (0 base + bonus_speed + allocated_speed) 
is applied to all users in the production database.

Usage:
    python3 migrations/migrate_recalculate_stats.py
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import Database
from models.user import Utente
from services.user_service import UserService

def migrate_stats():
    db = Database()
    session = db.get_session()
    user_service = UserService()
    
    try:
        users = session.query(Utente).all()
        total = len(users)
        print(f"[MIGRATION] Starting stat recalculation for {total} users...")
        
        for i, user in enumerate(users):
            # The service's recalculate_stats already uses the new formula
            user_service.recalculate_stats(user.id_telegram, session=session)
            
            if (i + 1) % 50 == 0:
                print(f"[MIGRATION] Processed {i + 1}/{total} users...")
        
        session.commit()
        print(f"[MIGRATION] ✅ Successfully updated stats for {total} users.")
        
    except Exception as e:
        print(f"[MIGRATION] ❌ Error during migration: {e}")
        session.rollback()
        raise
    finally:
        session.close()

if __name__ == "__main__":
    migrate_stats()
