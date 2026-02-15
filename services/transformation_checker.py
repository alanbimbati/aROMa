#!/usr/bin/env python3
"""Service to check and revert expired transformations"""
import sys
sys.path.insert(0, '/home/alan/Documenti/Coding/aroma')

from database import Database
from models.user import Utente
from datetime import datetime, timedelta

def check_and_revert_transformations():
    """Check all users and revert expired transformations"""
    db = Database()
    session = db.get_session()
    
    try:
        now = datetime.now()
        
        # Find users with expired transformations
        expired_users = session.query(Utente).filter(
            Utente.transformation_expires_at != None,
            Utente.transformation_expires_at <= now
        ).all()
        
        for user in expired_users:
            print(f"⏰ Reverting expired transformation for user {user.id_telegram} ({user.current_transformation})")
            
            # Get base character (need to find the original character before transformation)
            from services.character_loader import get_character_loader
            loader = get_character_loader()
            
            current_char = loader.get_character_by_id(user.livello_selezionato)
            if current_char and current_char.get('base_character_id'):
                base_id = current_char['base_character_id']
                
                # Revert to base
                user.livello_selezionato = base_id
                user.transformation_expires_at = None
                user.current_transformation = None
                
                print(f"  ✅ Reverted to base character ID {base_id}")
            else:
                # Just clear the expiry
                user.transformation_expires_at = None
                user.current_transformation = None
                print(f"  ⚠️ Could not find base character, cleared expiry")
        
        session.commit()
        print(f"\n✅ Checked and reverted {len(expired_users)} expired transformations")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        session.rollback()
    finally:
        session.close()

if __name__ == "__main__":
    check_and_revert_transformations()
