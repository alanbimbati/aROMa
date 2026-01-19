import sys
import os
import re
sys.path.append(os.getcwd())

from services.pve_service import PvEService
from services.user_service import UserService
from models.pve import Mob
from models.user import Utente
from models.dungeon import Dungeon
from settings import GRUPPO_AROMA, PointsName
from sqlalchemy import text

def verify_wumpa_scaling():
    print("\n--- Testing Wumpa Reward Scaling ---")
    pve = PvEService()
    user_service = UserService()
    session = pve.db.get_session()
    
    # 1. Setup User
    user_id = 999999
    user = session.query(Utente).filter_by(id_telegram=user_id).first()
    if not user:
        print("Creating test user...")
        user = Utente(id_telegram=user_id, nome="TestUser", username="TestUser", livello=1, exp=0, points=0)
        session.add(user)
        session.commit()
    else:
        # Ensure level is set
        if not user.livello:
            user.livello = 1
        if user.exp is None:
            user.exp = 0
        if user.points is None:
            user.points = 0
        session.commit()
    
    # Ensure user has no fatigue/status effects for clean test
    user.daily_wumpa_earned = 0
    user.active_status_effects = None
    session.commit()
    
    # 2. Test Case 1: Difficulty 1, 100 Damage -> Expected 5 Wumpa
    print("\nTest Case 1: Difficulty 1 (Trash), 100 Damage")
    
    # Clear mobs and participation
    session.execute(text("DELETE FROM combat_participation"))
    session.execute(text("DELETE FROM mob"))
    session.commit()
    
    # Spawn Mob
    pve.spawn_specific_mob(chat_id=GRUPPO_AROMA)
    mob = session.query(Mob).first()
    
    # Force stats
    mob.difficulty_tier = 1
    mob.health = 100
    mob.max_health = 100
    mob.resistance = 0
    mob.mob_level = 1
    
    # Reset cooldown
    user.last_attack_time = None
    session.commit()
    
    # Attack to Kill (100 dmg)
    # We need to pass the user object from the session that pve_service will use?
    # pve_service opens its own sessions. We should pass a detached user or just the ID?
    # attack_mob takes 'user' object. It uses user.id_telegram.
    
    # We need to make sure pve_service sees the updated mob.
    # pve_service.attack_mob opens a new session.
    
    success, msg, _ = pve.attack_mob(user, 100, mob_id=mob.id)
    
    print(f"Attack Result: {success}")
    # print(f"Message: {msg}")
    
    # Parse Reward
    # "👤 **TestUser**: 100/100 dmg -> ... Exp, {wumpa} Wumpa"
    match = re.search(r"TestUser\*\*: 100/100 dmg -> \d+ Exp, (\d+) " + re.escape(PointsName), msg)
    if match:
        wumpa = int(match.group(1))
        expected = int(100 * 0.05 * 1) # 5
        if wumpa == expected:
            print(f"✅ PASS: Got {wumpa} Wumpa (Expected {expected})")
        else:
            print(f"❌ FAIL: Got {wumpa} Wumpa (Expected {expected})")
    else:
        print(f"❌ FAIL: Could not parse reward from message: {msg}")

    # 3. Test Case 2: Difficulty 5 (Boss), 100 Damage -> Expected 25 Wumpa
    print("\nTest Case 2: Difficulty 5 (Hard), 100 Damage")
    
    # Clear mobs and participation
    session.execute(text("DELETE FROM combat_participation"))
    session.execute(text("DELETE FROM mob"))
    session.commit()
    
    # Spawn Mob
    pve.spawn_specific_mob(chat_id=GRUPPO_AROMA)
    mob = session.query(Mob).first()
    
    # Force stats
    mob.difficulty_tier = 5
    mob.health = 100
    mob.max_health = 100
    mob.resistance = 0
    mob.mob_level = 25
    
    # Reset cooldown
    user.last_attack_time = None
    session.commit()
    
    # Attack to Kill
    success, msg, _ = pve.attack_mob(user, 100, mob_id=mob.id)
    
    match = re.search(r"TestUser\*\*: 100/100 dmg -> \d+ Exp, (\d+) " + re.escape(PointsName), msg)
    if match:
        wumpa = int(match.group(1))
        expected = int(100 * 0.05 * 5) # 25
        if wumpa == expected:
            print(f"✅ PASS: Got {wumpa} Wumpa (Expected {expected})")
        else:
            print(f"❌ FAIL: Got {wumpa} Wumpa (Expected {expected})")
    else:
        print(f"❌ FAIL: Could not parse reward from message: {msg}")

    session.close()

if __name__ == "__main__":
    try:
        verify_wumpa_scaling()
    except Exception as e:
        print(f"An error occurred: {e}")
        import traceback
        traceback.print_exc()
