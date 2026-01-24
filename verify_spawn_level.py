from database import Database
from services.pve_service import PvEService
from models.pve import Mob

def verify_spawn_level():
    print("Initializing Database...")
    db = Database()
    pve = PvEService()
    session = db.get_session()
    
    # Cleanup
    session.query(Mob).filter_by(is_dead=False).delete()
    session.commit()
    
    ref_level = 50
    print(f"--- Testing Spawn Level Range (Reference: {ref_level}) ---")
    
    levels = []
    for i in range(20):
        # Pass ignore_limit=True to spawn multiple
        success, msg, mob_id = pve.spawn_specific_mob(mob_name=None, reference_level=ref_level, ignore_limit=True)
        if success:
            mob = session.query(Mob).filter_by(id=mob_id).first()
            levels.append(mob.mob_level)
            # Cleanup immediately
            session.delete(mob)
            session.commit()
            
    print(f"Spawned Levels: {levels}")
    
    min_level = min(levels)
    max_level = max(levels)
    
    print(f"Min: {min_level}, Max: {max_level}")
    
    if min_level >= ref_level - 10 and max_level <= ref_level + 10:
        print("✅ Levels are within range [-10, +10]")
    else:
        print("❌ Levels are OUT of range!")
        
    # Test Min Level 1
    print("\n--- Testing Min Level 1 ---")
    success, msg, mob_id = pve.spawn_specific_mob(mob_name=None, reference_level=1, ignore_limit=True)
    if success:
        mob = session.query(Mob).filter_by(id=mob_id).first()
        print(f"Reference 1 -> Spawned Level: {mob.mob_level}")
        if mob.mob_level >= 1:
            print("✅ Min level respected")
        else:
            print("❌ Min level violated")
        session.delete(mob)
        session.commit()

    session.close()

if __name__ == "__main__":
    verify_spawn_level()
