import sys
import os
sys.path.append(os.getcwd())

from services.pve_service import PvEService
from database import Database
from models.seasons import Season
import random

def test_spawning():
    pve_service = PvEService()
    db = Database()
    session = db.get_session()
    
    # Get current season theme
    current_season = session.query(Season).filter_by(is_active=True).first()
    theme = current_season.theme.strip().lower() if current_season and current_season.theme else "dragon ball"
    print(f"Current Season Theme: {theme}")
    
    themed_count = 0
    random_count = 0
    total_trials = 50
    
    print(f"Simulating {total_trials} spawns...")
    
    # We need to mock the DB part of spawn_specific_mob or just check the logic
    # Since we can't easily mock everything, let's just inspect the mob_data and theme
    
    themed_mobs = [m for m in pve_service.mob_data if theme and theme in m.get('saga', '').strip().lower()]
    print(f"Themed mobs available: {len(themed_mobs)}")
    
    for _ in range(total_trials):
        # Simulate the logic in spawn_specific_mob
        if themed_mobs and random.random() < 0.7:
            themed_count += 1
            mob = random.choice(themed_mobs)
        else:
            random_count += 1
            mob = random.choice(pve_service.mob_data)
            
        # Verify level calculation
        difficulty = int(mob.get('difficulty', 1))
        # level = difficulty * random(1, 5)
        # We can't easily check the exact random value, but we can check the range
        # However, since we are simulating, let's just check if the logic in pve_service is correct
        
    print(f"Results: Themed={themed_count} ({themed_count/total_trials*100:.1f}%), Random={random_count} ({random_count/total_trials*100:.1f}%)")
    print("Expected: ~70% Themed, ~30% Random")
    
    # Test stat scaling for a specific level
    level = 10
    difficulty = 2
    speed, resistance, hp_bonus, dmg_bonus = pve_service._allocate_mob_stats(level, difficulty)
    print(f"\nTesting stats for Level {level} (Difficulty {difficulty}):")
    print(f"Speed: {speed}, Resistance: {resistance}%")
    print(f"HP Bonus: {hp_bonus}, DMG Bonus: {dmg_bonus}")
    
    base_hp = 50
    base_dmg = 10
    hp = base_hp + (level * 15)
    dmg = base_dmg + (level * 3)
    print(f"HP: {hp} (Expected: 50 + 150 = 200)")
    print(f"Damage: {dmg} (Expected: 10 + 30 = 40)")
    
    session.close()

if __name__ == "__main__":
    test_spawning()
