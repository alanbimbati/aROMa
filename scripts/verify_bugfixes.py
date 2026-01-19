import sys
import os
sys.path.append(os.getcwd())

from services.pve_service import PvEService
from services.season_manager import SeasonManager
from models.seasons import SeasonClaimedReward, SeasonReward
from models.dungeon import Dungeon
from database import Database
from settings import GRUPPO_AROMA
from sqlalchemy import text

def test_mob_restrictions():
    print("\n--- Testing Mob Restrictions ---")
    pve = PvEService()
    session = pve.db.get_session()
    
    # Clear existing mobs for test
    print("Clearing existing mobs...")
    session.execute(text("DELETE FROM mob"))
    session.commit()
    
    # 1. Test Spawn in Wrong Group
    print(f"Test 1: Spawn in wrong group (ID: 12345)")
    success, msg, _ = pve.spawn_specific_mob(chat_id=12345)
    if not success and "solo nel gruppo ufficiale" in msg:
        print("✅ PASS: Prevented spawn in wrong group")
    else:
        print(f"❌ FAIL: Unexpected result: {success}, {msg}")

    # 2. Test Spawn in Correct Group
    print(f"Test 2: Spawn in correct group ({GRUPPO_AROMA})")
    success, msg, mob_id = pve.spawn_specific_mob(chat_id=GRUPPO_AROMA)
    if success:
        print("✅ PASS: Spawned in correct group")
    else:
        print(f"❌ FAIL: Could not spawn: {msg}")

    # 3. Test Single Mob Limit
    print("Test 3: Spawn second mob")
    success, msg, _ = pve.spawn_specific_mob(chat_id=GRUPPO_AROMA)
    if not success and "già un mob attivo" in msg:
        print("✅ PASS: Prevented second mob spawn")
    else:
        print(f"❌ FAIL: Unexpected result: {success}, {msg}")
        
    session.close()

def test_season_rewards():
    print("\n--- Testing Season Rewards ---")
    manager = SeasonManager()
    session = manager.db.get_session()
    
    # Mock user and season
    user_id = 999999
    season_id = 1
    reward_id = 1
    
    # Ensure clean state
    session.execute(text(f"DELETE FROM season_claimed_reward WHERE user_id={user_id}"))
    session.commit()
    
    # Create a dummy reward if not exists
    reward = session.query(SeasonReward).filter_by(id=reward_id).first()
    if not reward:
        print("Creating dummy reward...")
        reward = SeasonReward(id=reward_id, season_id=season_id, level_required=1, reward_type='points', reward_value='100', reward_name='Test Reward')
        session.add(reward)
        session.commit()
        
    # Manually insert a claim
    print("Simulating claimed reward...")
    claim = SeasonClaimedReward(user_id=user_id, season_id=season_id, reward_id=reward_id)
    session.add(claim)
    session.commit()
    
    # Check if it exists
    exists = session.query(SeasonClaimedReward).filter_by(user_id=user_id, reward_id=reward_id).first()
    if exists:
        print("✅ PASS: Claim record inserted successfully")
    else:
        print("❌ FAIL: Claim record not found")
        
    session.close()

if __name__ == "__main__":
    try:
        test_mob_restrictions()
        test_season_rewards()
    except Exception as e:
        print(f"An error occurred: {e}")
