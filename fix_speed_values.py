from database import Database
from models.user import Utente
import sys

def fix_speed_values():
    print("Starting speed value fix...")
    db = Database()
    session = db.get_session()
    
    try:
        users = session.query(Utente).all()
        count = 0
        for user in users:
            # Calculate expected speed based on allocated points
            # Assuming 1 point = 5 speed
            allocated = user.allocated_speed or 0
            expected_speed = allocated * 5
            
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
    fix_speed_values()
