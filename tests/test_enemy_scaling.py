import os
import sys
import random
import datetime
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Add project root to path
sys.path.append(os.getcwd())

from services.pve_service import PvEService
from models.user import Utente
from models.pve import Mob
from models.dungeon import Dungeon
from models.combat import CombatParticipation
from database import Database

def test_refined_enemy_scaling():
    pve_service = PvEService()
    
    test_levels = [1, 20, 50, 90]
    
    print("--- Testing Refined Enemy Level Scaling ---")
    
    for player_level in test_levels:
        print(f"\nPlayer Level: {player_level}")
        
        # Test Mob Spawning
        spawned_mobs = []
        for _ in range(10):
            success, msg, mob_id = pve_service.spawn_specific_mob(chat_id=-1, reference_level=player_level)
            if success:
                mob = pve_service.get_mob_details(mob_id)
                spawned_mobs.append(mob)
        
        print(f"  Spawned Mobs:")
        for mob in spawned_mobs:
            level = mob['level']
            diff = (level - 1) // 10 + 1
            print(f"    - {mob['name']} (Lv. {level}, Diff. {diff})")
            
            # Check level range
            if not (player_level + 1 <= level <= player_level + 10):
                print(f"      ❌ Level {level} out of range!")
            
            # Check if mob name matches expected difficulty (roughly)
            # This is hard to automate perfectly without a full map, but we can check specific cases
            if player_level == 50 and mob['name'] == "Cell Junior":
                print(f"      ❌ Cell Junior spawned for level 50 player! (Should be Difficulty 4, level 31-40)")

        # Test Boss Spawning
        spawned_bosses = []
        for _ in range(5):
            # Clear bosses for test
            session = pve_service.db.get_session()
            session.query(Mob).filter(Mob.is_boss == True, Mob.chat_id == -1).delete()
            session.commit()
            session.close()
            
            success, msg, mob_id = pve_service.spawn_boss(chat_id=-1, reference_level=player_level)
            if success:
                mob = pve_service.get_mob_details(mob_id)
                spawned_bosses.append(mob)

        print(f"  Spawned Bosses:")
        for boss in spawned_bosses:
            level = boss['level']
            diff = (level - 1) // 10 + 1
            print(f"    - {boss['name']} (Lv. {level}, Diff. {diff})")
            
            # Check level range
            if not (player_level + 5 <= level <= player_level + 12):
                print(f"      ❌ Level {level} out of range!")

    # Cleanup test mobs
    session = pve_service.db.get_session()
    session.query(Mob).filter(Mob.chat_id == -1).delete()
    session.commit()
    session.close()

if __name__ == "__main__":
    test_refined_enemy_scaling()
