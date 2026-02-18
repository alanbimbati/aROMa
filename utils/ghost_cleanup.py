"""
Ghost User Cleanup Function
Removes users who are not members of the official aROMa group or test group.
Only runs in production mode (test=0).
"""
from database import Database
from models.user import Utente
from settings import TEST, GRUPPO_AROMA

def cleanup_ghost_users(bot):
    """
    Remove users who are not members of the official group.
    Only runs if TEST_MODE = 0 (production).
    """
    if TEST == 1:
        print("[GHOST_CLEANUP] Skipping cleanup - Test mode enabled")
        return
    
    print("[GHOST_CLEANUP] Starting ghost user cleanup...")
    db = Database()
    session = db.get_session()
    
    try:
        all_users = session.query(Utente).all()
        removed_count = 0
        kept_count = 0
        
        for user in all_users:
            user_id = user.id_telegram
            try:
                # Check if user is a member of the official group
                member = bot.get_chat_member(GRUPPO_AROMA, user_id)
                
                # If user is kicked/left/not a member, delete them
                if member.status in ['left', 'kicked']:
                    print(f"[GHOST_CLEANUP] Removing user {user_id} (status: {member.status})")
                    session.delete(user)
                    removed_count += 1
                else:
                    kept_count += 1
                    
            except Exception as e:
                # User not found in group or other error
                print(f"[GHOST_CLEANUP] Error checking user {user_id}: {e}")
                print(f"[GHOST_CLEANUP] Removing user {user_id} (not in group)")
                session.delete(user)
                removed_count += 1
        
        session.commit()
        print(f"[GHOST_CLEANUP] Cleanup complete. Removed: {removed_count}, Kept: {kept_count}")
        
    except Exception as e:
        print(f"[GHOST_CLEANUP] Error during cleanup: {e}")
        session.rollback()
    finally:
        session.close()
