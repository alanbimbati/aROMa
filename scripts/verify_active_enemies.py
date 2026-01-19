import sys
import os
sys.path.append(os.getcwd())

from services.pve_service import PvEService
from models.pve import Mob
from models.dungeon import Dungeon
from settings import GRUPPO_AROMA
from sqlalchemy import text

def verify_active_enemies():
    print("\n--- Testing Active Enemies List ---")
    pve = PvEService()
    session = pve.db.get_session()
    
    # 1. Clear existing mobs
    session.execute(text("DELETE FROM mob"))
    session.commit()
    
    # 2. Verify empty list
    mobs = pve.get_active_mobs(GRUPPO_AROMA)
    print(f"Active mobs (Empty): {len(mobs)}")
    if len(mobs) == 0:
        print("✅ PASS: Empty list correct")
    else:
        print(f"❌ FAIL: Expected 0, got {len(mobs)}")
        
    # 3. Spawn mobs
    print("\nSpawning mobs...")
    pve.spawn_specific_mob(chat_id=GRUPPO_AROMA)
    pve.spawn_specific_mob(chat_id=GRUPPO_AROMA)
    
    # 4. Verify list content
    mobs = pve.get_active_mobs(GRUPPO_AROMA)
    print(f"Active mobs (Spawned): {len(mobs)}")
    
    if len(mobs) >= 1: # Might be limited to 1 by previous bug fix
        print(f"✅ PASS: Found {len(mobs)} mobs")
        for mob in mobs:
            print(f" - {mob.name} (HP: {mob.health}/{mob.max_health})")
    else:
        print("❌ FAIL: No mobs found after spawn")
        
    session.close()

if __name__ == "__main__":
    try:
        verify_active_enemies()
    except Exception as e:
        print(f"An error occurred: {e}")
        import traceback
        traceback.print_exc()
