from database import Database
from models.user import Utente
import sys

def fix_base_stats():
    print("Starting fix for Base Stats (Health=100, Mana=50, Dmg=10)...")
    db = Database()
    session = db.get_session()
    
    # Constants
    BASE_HEALTH = 100
    BASE_MANA = 50
    BASE_DAMAGE = 10
    
    HEALTH_PER_POINT = 10
    MANA_PER_POINT = 5
    DAMAGE_PER_POINT = 2
    
    try:
        users = session.query(Utente).all()
        count = 0
        for user in users:
            updates = False
            
            # Health
            allocated_health = user.allocated_health or 0
            expected_max_health = BASE_HEALTH + (allocated_health * HEALTH_PER_POINT)
            if user.max_health != expected_max_health:
                print(f"Fixing {user.username}: Max Health {user.max_health} -> {expected_max_health}")
                user.max_health = expected_max_health
                # Also fix current health if it exceeds max
                if user.health > expected_max_health:
                    user.health = expected_max_health
                updates = True
                
            # Mana
            allocated_mana = user.allocated_mana or 0
            expected_max_mana = BASE_MANA + (allocated_mana * MANA_PER_POINT)
            if user.max_mana != expected_max_mana:
                print(f"Fixing {user.username}: Max Mana {user.max_mana} -> {expected_max_mana}")
                user.max_mana = expected_max_mana
                if user.mana > expected_max_mana:
                    user.mana = expected_max_mana
                updates = True
                
            # Damage
            allocated_damage = user.allocated_damage or 0
            expected_damage = BASE_DAMAGE + (allocated_damage * DAMAGE_PER_POINT)
            if user.base_damage != expected_damage:
                print(f"Fixing {user.username}: Damage {user.base_damage} -> {expected_damage}")
                user.base_damage = expected_damage
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
    fix_base_stats()
