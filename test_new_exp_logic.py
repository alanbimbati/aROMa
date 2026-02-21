
import sys
import os
from unittest.mock import MagicMock

# Set environment
sys.path.append(os.getcwd())

from services.reward_service import RewardService

class MockMob:
    def __init__(self, level, tier, max_health, dungeon_id=None, is_boss=False, name="Mob"):
        self.mob_level = level
        self.difficulty_tier = tier
        self.max_health = max_health
        self.dungeon_id = dungeon_id
        self.is_boss = is_boss
        self.name = name

class MockParticipant:
    def __init__(self, user_id, damage):
        self.user_id = user_id
        self.damage_dealt = damage

def test_logic():
    # Mock dependencies
    db = MagicMock()
    user_service = MagicMock()
    season_manager = MagicMock()
    item_service = MagicMock()
    
    reward_service = RewardService(db, user_service, item_service, season_manager)
    
    print("--- TESTING HP SCALING ---")
    # Low HP Mob
    mob_low = MockMob(level=50, tier=5, max_health=500)
    # High HP Mob (but same level/tier)
    mob_high = MockMob(level=50, tier=5, max_health=10000)
    
    p = MockParticipant(1, 100)
    
    res_low = reward_service.calculate_rewards(mob_low, [p])
    res_high = reward_service.calculate_rewards(mob_high, [p])
    
    xp_low = res_low[0]['base_xp']
    xp_high = res_high[0]['base_xp']
    
    print(f"Lv 50, 500 HP: {xp_low} XP")
    print(f"Lv 50, 10000 HP: {xp_high} XP")
    
    if xp_high > xp_low * 2:
        print("✅ HP Scaling is working!")
    else:
        print("❌ HP Scaling might be too weak.")

    print("\n--- TESTING DUNGEON EXP REMOVAL ---")
    mob_dungeon = MockMob(level=10, tier=1, max_health=1000, dungeon_id=1)
    
    # Mock user
    user = MagicMock()
    user.id_telegram = 1
    user.current_hp = 100
    user.health = 100
    user.has_turbo = False
    
    session = MagicMock()
    session.query().filter().all.return_value = [user]
    session.query().filter_by().first.return_value = None # No status effects
    
    rewards_dungeon_data = reward_service.calculate_rewards(mob_dungeon, [p])
    # distribute_rewards returns a summary string usually
    reward_service.user_service = user_service
    reward_service.distribute_rewards(rewards_dungeon_data, mob_dungeon, session)
    
    # Check if add_exp_by_id was called with 0
    # or check the rewards_dungeon_data if we modify it in distribute
    # Let's check how many times add_exp_by_id was called with xp=0
    
    # We need to see if xp was set to 0 in the loop
    # Actually, let's just inspect the logic in reward_service.py:146-150
    print("Verifying dungeon XP is 0...")
    # Mocking the session.query for Utente
    
    # Let's use distribute_rewards logic manually or check call args
    reward_service.distribute_rewards(rewards_dungeon_data, mob_dungeon, session)
    
    # Capture calls to user_service.add_exp_by_id
    args, kwargs = user_service.add_exp_by_id.call_args
    target_id, xp = args[:2]
    print(f"EXP distributed for dungeon mob: {xp}")
    
    if xp == 0:
        print("✅ Dungeon EXP correctly set to 0!")
    else:
        print(f"❌ Dungeon EXP is {xp}, should be 0.")

if __name__ == "__main__":
    test_logic()
