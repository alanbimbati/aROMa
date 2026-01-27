import sys
import os
sys.path.append(os.getcwd())

from services.dungeon_service import DungeonService
from services.pve_service import PvEService
from services.user_service import UserService
from models.user import Utente
from models.dungeon import Dungeon
from models.pve import Mob
from database import Database
import time
import settings
import services.pve_service

# Monkeypatch settings to allow spawning in test chat
# Note: pve_service imports GRUPPO_AROMA directly, so we must patch it there too
settings.GRUPPO_AROMA = 62716473
services.pve_service.GRUPPO_AROMA = 62716473

def verify_dungeons():
    print("🚀 Starting Dungeon System Verification...")
    
    db = Database()
    session = db.get_session()
    
    # Setup Test User
    user_id = 62716473 # Alan
    us = UserService()
    u = us.get_user(user_id)
    if not u:
        print("User not found, skipping verification")
        return
    
    # Clear previous test dungeons
    session.query(Dungeon).filter_by(chat_id=user_id).delete()
    session.query(Mob).filter_by(chat_id=user_id).delete()
    session.commit()
    session.close()
    
    ds = DungeonService()
    pve = PvEService()
    
    # 1. List Dungeons
    print("\n📜 Loading Dungeons...")
    dungeons = ds.load_dungeons()
    print(f"Loaded {len(dungeons)} dungeons.")
    assert len(dungeons) >= 20, "Should have at least 20 dungeons"
    
    # 2. Create Dungeon 1 (Raditz Invasion)
    print("\n🏰 Creating Dungeon 1...")
    d_id, msg = ds.create_dungeon(user_id, 1, user_id)
    print(msg)
    assert d_id is not None, "Failed to create dungeon"
    
    # 3. Start Dungeon
    print("\n⚔️ Starting Dungeon...")
    success, msg = ds.start_dungeon(user_id)
    print(msg)
    assert success, "Failed to start dungeon"
    
    # 4. Simulate Combat (Step 1: 3x Saibaman)
    print("\n👊 Simulating Step 1 Combat...")
    
    # DEBUG: Try direct spawn
    print("DEBUG: Attempting direct spawn of Saibaman...")
    s, m, mid = pve.spawn_specific_mob("Saibaman", user_id)
    print(f"Direct Spawn Result: {s}, {m}, {mid}")
    
    session = db.get_session()
    mobs = session.query(Mob).filter_by(dungeon_id=d_id, is_dead=False).all()
    print(f"Found {len(mobs)} mobs in Step 1.")
    assert len(mobs) == 3, f"Expected 3 mobs, found {len(mobs)}"
    
    # Kill all mobs
    for mob in mobs:
        print(f"Killing {mob.name}...")
        mob.health = 0
        mob.is_dead = True
        session.commit()
        
        # Trigger check
        msg = ds.check_step_completion(d_id)
        if msg:
            print(f"Step Completion Msg: {msg}")
            
    session.close()
    
    # 5. Verify Step 2 (Raditz Boss)
    print("\n👊 Simulating Step 2 (Boss)...")
    session = db.get_session()
    dungeon = session.query(Dungeon).filter_by(id=d_id).first()
    assert dungeon.current_stage == 2, f"Expected Stage 2, got {dungeon.current_stage}"
    
    boss = session.query(Mob).filter_by(dungeon_id=d_id, is_dead=False).first()
    assert boss is not None, "Boss not spawned"
    print(f"Boss spawned: {boss.name}")
    
    # Kill Boss
    boss.health = 0
    boss.is_dead = True
    session.commit()
    session.close()
    
    msg = ds.check_step_completion(d_id)
    print(f"Dungeon Completion Msg: {msg}")
    
    # 6. Verify Completion and Score
    session = db.get_session()
    dungeon = session.query(Dungeon).filter_by(id=d_id).first()
    assert dungeon.status == "completed", "Dungeon should be completed"
    print(f"Final Score: {dungeon.score}")
    print(f"Stats: {dungeon.stats}")
    
    # 7. Verify Progression (Can access Dungeon 2)
    print("\n🔓 Verifying Progression...")
    can_access_2 = ds.can_access_dungeon(user_id, 2)
    print(f"Can access Dungeon 2? {can_access_2}")
    assert can_access_2, "Should be able to access Dungeon 2"
    
    print("\n✅ Verification Successful!")

if __name__ == "__main__":
    verify_dungeons()
