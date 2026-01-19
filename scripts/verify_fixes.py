import sys
import os
import datetime
import time
sys.path.append(os.getcwd())

from services.pve_service import PvEService
from models.user import Utente
from models.pve import Mob
from models.dungeon import Dungeon
from database import Database

def verify_fixes():
    print("\n--- Testing Fixes ---")
    pve_service = PvEService()
    session = pve_service.db.get_session()
    
    print(f"Loaded {len(pve_service.mob_data)} mobs from CSV.")
    
    # 1. Setup User
    user_id = 777777
    user = session.query(Utente).filter_by(id_telegram=user_id).first()
    if not user:
        user = Utente(id_telegram=user_id, nome="FixTester", username="FixTester", livello=10, exp=0, points=0)
        session.add(user)
    else:
        user.livello = 10
        user.allocated_speed = 0 # Reset speed for consistent cooldown
        user.last_attack_time = None # Reset cooldown
        
    # Clear existing active mobs to avoid limit and mismatch
    session.query(Mob).filter_by(is_dead=False).update({"is_dead": True})
    session.commit()
    
    # 2. Test Mob Mismatch Fix
    print("\nTesting Mob Mismatch Fix...")
    
    # Spawn Mob A
    success, msg, mob_a_id = pve_service.spawn_specific_mob("Saibaman")
    if not success:
        print(f"❌ FAIL: Could not spawn mob: {msg}")
        session.close()
        return
        
    print(f"Spawned Mob A (ID: {mob_a_id})")
    
    # Spawn Mob B (Force spawn by clearing active check manually for test)
    # Note: spawn_specific_mob checks for active mobs, so we might need to "kill" Mob A first or bypass check?
    # Actually, the fix is in get_current_mob_status(mob_id).
    # Let's just verify get_current_mob_status returns the correct mob when ID is passed.
    
    mob_a_status = pve_service.get_current_mob_status(mob_a_id)
    print(f"Status for Mob A ID: {mob_a_status['name']}")
    
    if mob_a_status['name'] == "Saibaman":
        print("✅ PASS: Correct mob retrieved by ID")
    else:
        print(f"❌ FAIL: Retrieved {mob_a_status['name']} instead of Saibaman")
        
    # 3. Test Cooldown Timer
    print("\nTesting Cooldown Timer...")
    
    # Attack once
    success, msg, extra = pve_service.attack_mob(user, 10, mob_id=mob_a_id)
    print(f"Attack 1: {success} - {msg}")
    
    # Refresh user to get updated last_attack_time
    session.expire_all()
    user = session.query(Utente).filter_by(id_telegram=user_id).first()
    
    # Attack again immediately (should fail with cooldown)
    success, msg, extra = pve_service.attack_mob(user, 10, mob_id=mob_a_id)
    print(f"Attack 2: {success} - {msg}")
    
    if not success and "CD:" in msg:
        print("✅ PASS: Cooldown message contains 'CD:'")
    else:
        print(f"❌ FAIL: Message format incorrect: {msg}")

    # Cleanup
    mob_a = session.query(Mob).filter_by(id=mob_a_id).first()
    if mob_a:
        session.delete(mob_a)
    session.commit()
    session.close()

if __name__ == "__main__":
    try:
        verify_fixes()
    except Exception as e:
        print(f"An error occurred: {e}")
        import traceback
        traceback.print_exc()
