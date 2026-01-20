from database import Database
from models.user import Utente
import sys

def fix_all_stats_final():
    print("Starting final fix for Resistance and Crit (1 point = 1 value)...")
    db = Database()
    session = db.get_session()
    
    try:
        users = session.query(Utente).all()
        count = 0
        for user in users:
            # Resistance
            allocated_res = user.allocated_resistance or 0
            expected_res = allocated_res
            
            # Crit
            allocated_crit = user.allocated_crit or 0
            expected_crit = allocated_crit
            
            updates = False
            if user.resistance != expected_res:
                print(f"Fixing user {user.username or user.id_telegram}: Resistance {user.resistance} -> {expected_res}")
                user.resistance = expected_res
                updates = True
                
            if user.crit_chance != expected_crit:
                print(f"Fixing user {user.username or user.id_telegram}: Crit {user.crit_chance} -> {expected_crit}")
                user.crit_chance = expected_crit
                updates = True
                
            if updates:
                count += 1
                
        session.commit()
        print(f"Fixed {count} users.")
    except Exception as e:
        print(f"Error: {e}")
        session.rollback()
    finally:
        session.close()

if __name__ == "__main__":
    fix_all_stats_final()
