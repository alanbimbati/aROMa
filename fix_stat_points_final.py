from database import Database
from models.user import Utente
import sys

def fix_stat_points_final():
    print("Recalculating stat points (2/lvl < 80, 5/lvl >= 80)...")
    db = Database()
    session = db.get_session()
    
    try:
        users = session.query(Utente).all()
        count = 0
        for user in users:
            level = user.livello or 1
            
            # Calculate Total Earned Points
            if level < 80:
                total_earned = (level - 1) * 2
            else:
                # Levels 1-79 give 2 points each (79 levels * 2 = 158? No, level 1 gives 0. So 78 steps?
                # Level 1 -> 2 is 1 step.
                # Level 1 -> 80 is 79 steps.
                # Steps 1 to 79 (Level 2 to 80).
                # Wait, "da lv 80" means level 80 gives 5 points.
                # So levels 2..79 give 2 points (78 levels). 78 * 2 = 156.
                # Level 80 gives 5 points.
                # So at level 80, total = 156 + 5 = 161.
                # Formula: 156 + (level - 79) * 5
                total_earned = 156 + (level - 79) * 5
            
            # Calculate Allocated Points
            allocated = (user.allocated_health or 0) + \
                        (user.allocated_mana or 0) + \
                        (user.allocated_damage or 0) + \
                        (user.allocated_speed or 0) + \
                        (user.allocated_resistance or 0) + \
                        (user.allocated_crit or 0)
            
            expected_available = max(0, total_earned - allocated)
            
            if user.stat_points != expected_available:
                print(f"Fixing {user.username}: Level {level}, Total {total_earned}, Alloc {allocated}. Points {user.stat_points} -> {expected_available}")
                user.stat_points = expected_available
                count += 1
                
        session.commit()
        print(f"Fixed {count} users.")
    except Exception as e:
        print(f"Error: {e}")
        session.rollback()
    finally:
        session.close()

if __name__ == "__main__":
    fix_stat_points_final()
