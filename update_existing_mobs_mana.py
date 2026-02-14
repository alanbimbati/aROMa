from database import Database
from models.pve import Mob
from services.pve_service import PvEService

db = Database()
session = db.get_session()
pve_service = PvEService()

try:
    # Get all mobs with 0 or NULL mana
    mobs_to_update = session.query(Mob).filter(
        (Mob.mana == 0) | (Mob.mana == None) | (Mob.max_mana == 0) | (Mob.max_mana == None)
    ).all()
    
    print(f"Found {len(mobs_to_update)} mobs to update")
    
    for mob in mobs_to_update:
        level = mob.mob_level if mob.mob_level else 1
        
        # Calculate mana using the same formula as spawn
        max_mana = pve_service._calculate_character_mana(mob.name, level, is_boss=mob.is_boss)
        
        mob.max_mana = max_mana
        mob.mana = max_mana  # Set to full mana
        
        print(f"Updated {mob.name} (Lv {level}, Boss: {mob.is_boss}): {max_mana} mana")
    
    session.commit()
    print(f"\n✅ Successfully updated {len(mobs_to_update)} mobs with mana")
    
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()
    session.rollback()
finally:
    session.close()
