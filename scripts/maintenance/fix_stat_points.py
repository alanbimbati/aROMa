import sys
import os

# Add parent directory to path to import modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from database import Database
from models.user import Utente

def calculate_expected_points(level):
    """
    Calculate expected total stat points based on level.
    Levels 1-79: 2 points per level up (starting from level 2)
    Levels 80+: 5 points per level up
    """
    if level <= 1:
        return 0
    
    if level < 80:
        return (level - 1) * 2
    else:
        # Points for 1-79 (79 level ups * 2 = 158)
        # Points for 80+ (level - 80) * 5
        # Example: Level 80. (79*2) + (1*5) = 158 + 5 = 163?
        # No, level 80 is the 80th level. You leveled up FROM 79 TO 80.
        # So at level 80 you have leveled up 79 times.
        # If the switch happens AT level 80 (meaning going from 79 to 80 gives 5 points):
        # Then: (78 * 2) + 5 = 156 + 5 = 161.
        # Let's check user_service logic:
        # points_to_add = 5 if utente.livello >= 80 else 2
        # This runs AFTER incrementing level.
        # So if I go from 79 -> 80. utente.livello is 80. 80 >= 80 is True. So I get 5 points.
        # So levels 2..79 (78 level ups) give 2 points.
        # Levels 80..L give 5 points.
        
        points_low = 78 * 2  # Level ups to reach level 79
        points_high = (level - 79) * 5 # Level ups from 79 to L
        return points_low + points_high

def fix_stat_points():
    print("Starting stat points fix...")
    db = Database()
    session = db.get_session()
    
    try:
        users = session.query(Utente).all()
        count = 0
        
        for user in users:
            expected_total = calculate_expected_points(user.livello)
            
            # Calculate currently spent points
            spent = (user.allocated_health or 0) + (user.allocated_mana or 0) + (user.allocated_damage or 0)
            
            # Current available should be expected - spent
            current_available = user.stat_points
            
            new_available = expected_total - spent
            
            if new_available != current_available:
                print(f"Fixing user {user.username or user.nome} (Lv {user.livello}):")
                print(f"  Expected Total: {expected_total}")
                print(f"  Spent: {spent}")
                print(f"  Current Available: {current_available}")
                print(f"  New Available: {new_available}")
                
                user.stat_points = new_available
                count += 1
        
        if count > 0:
            session.commit()
            print(f"\n✅ Fixed {count} users.")
        else:
            print("\n✅ All users already have correct stat points.")
            
    except Exception as e:
        session.rollback()
        print(f"Error: {e}")
    finally:
        session.close()

if __name__ == "__main__":
    fix_stat_points()
