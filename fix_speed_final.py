from database import Database
from models.user import Utente
import sys

def fix_speed_final():
    print("Starting final speed value fix (1 point = 1 speed)...")
    db = Database()
    session = db.get_session()
    
    try:
        users = session.query(Utente).all()
        count = 0
        for user in users:
            # New logic: Speed is exactly equal to allocated points
            # (unless we add base speed later, but for now it's 0 base)
            allocated = user.allocated_speed or 0
            expected_speed = allocated
            
            if user.speed != expected_speed:
                print(f"Fixing user {user.username or user.id_telegram}: Speed {user.speed} -> {expected_speed} (Allocated: {allocated})")
                user.speed = expected_speed
                count += 1
                
        session.commit()
        print(f"Fixed {count} users.")
    except Exception as e:
        print(f"Error: {e}")
        session.rollback()
    finally:
        session.close()

if __name__ == "__main__":
    fix_speed_final()
