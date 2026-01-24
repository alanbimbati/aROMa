from database import Database
from services.pve_service import PvEService
from models.pve import Mob

def verify_spawn_limit():
    print("Initializing Database...")
    db = Database()
    pve = PvEService()
    session = db.get_session()
    
    # Cleanup existing mobs
    session.query(Mob).filter_by(is_dead=False).delete()
    session.commit()
    
    print("--- Test 1: Spawn First Mob ---")
    success, msg, mob1_id = pve.spawn_specific_mob(mob_name=None, reference_level=1)
    print(f"Spawn 1 Result: {success} (ID: {mob1_id})")
    
    if not success:
        print("❌ Failed to spawn first mob!")
        return
        
    print("--- Test 2: Spawn Second Mob (Should Fail) ---")
    success, msg, mob2_id = pve.spawn_specific_mob(mob_name=None, reference_level=1)
    print(f"Spawn 2 Result: {success} (Msg: {msg})")
    
    if success:
        print("❌ Spawn 2 succeeded but should have failed!")
    else:
        print("✅ Spawn 2 failed as expected.")
        
    print("--- Test 3: Spawn Dungeon Mob (Should Succeed) ---")
    # Simulate dungeon spawn by passing ignore_limit=True
    success, msg, mob3_id = pve.spawn_specific_mob(mob_name=None, reference_level=1, ignore_limit=True)
    print(f"Spawn 3 Result: {success} (ID: {mob3_id})")
    
    if success:
        print("✅ Dungeon spawn succeeded.")
    else:
        print("❌ Dungeon spawn failed.")
        
    # Cleanup
    session.query(Mob).filter(Mob.id.in_([mob1_id, mob3_id])).delete()
    session.commit()
    session.close()

if __name__ == "__main__":
    verify_spawn_limit()
