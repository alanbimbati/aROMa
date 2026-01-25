from database import Database
from services.user_service import UserService
from services.pve_service import PvEService
from models.user import Utente
from models.pve import Mob
from models.combat import CombatParticipation
import datetime

def verify_pve_fixes():
    print("Initializing Database...")
    db = Database()
    us = UserService()
    pve = PvEService()
    session = db.get_session()
    
    # Setup Test User
    user_id = 999999
    session.query(Utente).filter_by(id_telegram=user_id).delete()
    session.commit()
    
    u = Utente(id_telegram=user_id, username="PvETester", nome="Tester", health=100, max_health=100, current_hp=100, shield_hp=0)
    session.add(u)
    session.commit()
    
    print("\n--- Test 1: UserService.damage_health ---")
    # 1. Normal Damage
    new_hp, died = us.damage_health(u, 20)
    session.refresh(u)
    print(f"Damage 20 -> HP: {new_hp}, Died: {died}")
    if new_hp == 80 and not died:
        print("✅ Normal damage working")
    else:
        print("❌ Normal damage failed")
        
    # 2. Shield Damage
    u.shield_hp = 50
    session.commit()
    new_hp, died = us.damage_health(u, 30) # Should take all from shield
    session.refresh(u)
    print(f"Shield 50, Damage 30 -> HP: {new_hp}, Shield: {u.shield_hp}, Died: {died}")
    if new_hp == 80 and u.shield_hp == 20:
        print("✅ Shield partial absorption working")
    else:
        print(f"❌ Shield partial failed (HP: {new_hp}, Shield: {u.shield_hp})")
        
    # 3. Shield Break + Overflow
    new_hp, died = us.damage_health(u, 40) # 20 shield, 20 HP
    session.refresh(u)
    print(f"Shield 20, Damage 40 -> HP: {new_hp}, Shield: {u.shield_hp}, Died: {died}")
    if new_hp == 60 and u.shield_hp == 0:
        print("✅ Shield break overflow working")
    else:
        print("❌ Shield break failed")
        
    # 4. Death
    new_hp, died = us.damage_health(u, 100)
    session.refresh(u)
    print(f"Damage 100 -> HP: {new_hp}, Died: {died}")
    if died:
        print("✅ Death check working")
    else:
        print("❌ Death check failed")
        
    print("\n--- Test 2: PvEService.mob_random_attack (Fix Confirmation) ---")
    # Create a dummy mob
    mob = Mob(name="TestMob", health=100, max_health=100, attack_damage=10, is_dead=False)
    session.add(mob)
    session.commit()
    
    # Revive user
    u.current_hp = 100
    u.health = 100
    session.commit()
    
    # Mock user_service.get_recent_users to return our user
    original_get_recent = us.get_recent_users
    us.get_recent_users = lambda chat_id=None: [user_id]
    pve.user_service = us # Inject patched service
    
    try:
        pve.mob_random_attack(specific_mob_id=mob.id)
        print("✅ mob_random_attack executed without AttributeError")
    except AttributeError as e:
        print(f"❌ AttributeError still present: {e}")
    except Exception as e:
        print(f"❌ Other error: {e}")
    finally:
        us.get_recent_users = original_get_recent
        
    print("\n--- Test 3: PvEService.attack_mob (Death & Rewards) ---")
    # Reset mob
    mob.health = 10
    mob.max_health = 100
    session.commit()
    
    # Add participation
    part = CombatParticipation(user_id=user_id, mob_id=mob.id, damage_dealt=0)
    session.add(part)
    session.commit()
    
    # Attack to kill
    print("Attacking mob to kill...")
    success, msg, extra = pve.attack_mob(u, base_damage=20, mob_id=mob.id)
    
    session.refresh(mob)
    print(f"Mob Dead? {mob.is_dead}")
    print(f"Result Msg: {msg[:100]}...")
    
    if mob.is_dead and "sconfitto" in msg:
        print("✅ Mob died and death message generated")
    else:
        print("❌ Mob did NOT die or message missing")
        
    if "Ricompense" in msg:
        print("✅ Rewards mentioned in message")
    else:
        print("❌ Rewards NOT mentioned")

    # Cleanup
    session.delete(mob)
    session.query(Utente).filter_by(id_telegram=user_id).delete()
    session.commit()
    session.close()

if __name__ == "__main__":
    verify_pve_fixes()
