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

def verify_aoe():
    print("\n--- Testing AoE Attacks ---")
    pve_service = PvEService()
    session = pve_service.db.get_session()
    
    # 1. Setup User
    user_id = 888888
    user = session.query(Utente).filter_by(id_telegram=user_id).first()
    if not user:
        user = Utente(id_telegram=user_id, nome="AoETester", username="AoETester", livello=10, exp=0, points=0, mana=100)
        session.add(user)
    else:
        user.mana = 100
        user.last_attack_time = None
        
    # Clear existing active mobs
    session.query(Mob).filter_by(is_dead=False).update({"is_dead": True})
    session.commit()
    
    # 2. Spawn multiple mobs
    chat_id = -100123456789 # Mock group ID
    
    # We need to bypass the "max 1 active mob" check for testing AoE
    # So we'll create them manually
    mob1 = Mob(name="Mob1", health=100, max_health=100, chat_id=chat_id, is_dead=False)
    mob2 = Mob(name="Mob2", health=100, max_health=100, chat_id=chat_id, is_dead=False)
    session.add(mob1)
    session.add(mob2)
    session.commit()
    
    print(f"Spawned 2 mobs in chat {chat_id}")
    
    # 3. Perform AoE Attack
    base_damage = 50
    success, msg, extra = pve_service.attack_aoe(user, base_damage, chat_id=chat_id)
    
    print(f"AoE Attack: {success} - {msg}")
    
    if success:
        # Verify mana
        session.refresh(user)
        print(f"User Mana: {user.mana} (Expected: 70)")
        if user.mana == 70:
            print("✅ PASS: Mana deducted correctly")
        else:
            print("❌ FAIL: Mana not deducted correctly")
            
        # Verify damage on mobs
        session.refresh(mob1)
        session.refresh(mob2)
        print(f"Mob1 Health: {mob1.health} (Expected: < 100)")
        print(f"Mob2 Health: {mob2.health} (Expected: < 100)")
        
        if mob1.health < 100 and mob2.health < 100:
            print("✅ PASS: Both mobs took damage")
        else:
            print("❌ FAIL: One or both mobs did not take damage")
            
        # Verify cooldown
        success2, msg2, extra2 = pve_service.attack_aoe(user, base_damage, chat_id=chat_id)
        print(f"Immediate AoE Attack 2: {success2} - {msg2}")
        if not success2 and "CD AoE" in msg2:
            print("✅ PASS: AoE Cooldown applied")
        else:
            print("❌ FAIL: AoE Cooldown not applied correctly")
    else:
        print("❌ FAIL: AoE Attack failed")

    # Cleanup
    session.query(Mob).filter_by(chat_id=chat_id).delete()
    session.commit()
    session.close()

if __name__ == "__main__":
    try:
        verify_aoe()
    except Exception as e:
        print(f"An error occurred: {e}")
        import traceback
        traceback.print_exc()
