import sys
import os
import datetime
sys.path.append(os.getcwd())

from services.user_service import UserService
from models.user import Utente
from settings import GRUPPO_AROMA
from sqlalchemy import text

def verify_shield_system():
    print("\n--- Testing Shield System ---")
    user_service = UserService()
    session = user_service.db.get_session()
    
    # 1. Setup User
    user_id = 888888
    user = session.query(Utente).filter_by(id_telegram=user_id).first()
    if not user:
        user = Utente(id_telegram=user_id, nome="ShieldUser", username="ShieldUser", livello=10, exp=0, points=0)
        session.add(user)
    else:
        user.livello = 10
        
    # Give resistance and HP
    user.allocated_resistance = 15
    user.max_health = 1000
    user.health = 1000
    user.current_hp = 1000
    user.shield_hp = 0
    session.commit()
    
    # 2. Cast Shield
    print("\nCasting Shield...")
    shield_amount = 200
    user_service.cast_shield(user, shield_amount)
    session.refresh(user)
    
    print(f"Shield HP: {user.shield_hp}")
    if user.shield_hp == 200:
        print("✅ PASS: Shield cast correctly")
    else:
        print(f"❌ FAIL: Shield HP is {user.shield_hp}")
        
    # 3. Take Damage (Absorbed)
    print("\nTaking 100 Damage (Should be absorbed)...")
    # Note: damage_health applies 25% mitigation if shield is up
    # Incoming 100 -> Reduced by 25% (assuming 0 base res + 25 shield) -> 75 damage
    # Shield 200 -> 125
    
    # Reset resistance for calculation clarity
    user.resistance = 0
    session.commit()
    
    new_hp, died = user_service.damage_health(user, 100)
    session.refresh(user)
    
    print(f"New Shield HP: {user.shield_hp}")
    print(f"New HP: {user.current_hp}")
    
    # Expected: 100 * 0.75 = 75 damage to shield. Shield = 125. HP = 1000.
    if user.shield_hp == 125 and user.current_hp == 1000:
        print("✅ PASS: Damage absorbed correctly")
    else:
        print(f"❌ FAIL: Shield={user.shield_hp}, HP={user.current_hp}")
        
    # 4. Take Damage (Break)
    print("\nTaking 200 Damage (Should break shield)...")
    # Shield has 125.
    # Incoming 200 -> Reduced by 25% -> 150 damage.
    # Shield takes 125 -> 0.
    # Remaining 25 damage goes to HP.
    # HP 1000 -> 975.
    
    new_hp, died = user_service.damage_health(user, 200)
    session.refresh(user)
    
    print(f"New Shield HP: {user.shield_hp}")
    print(f"New HP: {user.current_hp}")
    
    if user.shield_hp == 0 and user.current_hp == 975:
        print("✅ PASS: Shield broken and overflow damage applied")
    else:
        print(f"❌ FAIL: Shield={user.shield_hp}, HP={user.current_hp}")

    session.close()

if __name__ == "__main__":
    try:
        verify_shield_system()
    except Exception as e:
        print(f"An error occurred: {e}")
        import traceback
        traceback.print_exc()
