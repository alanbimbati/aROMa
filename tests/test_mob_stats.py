import unittest
import sys
import os

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from services.pve_service import PvEService

class TestMobStats(unittest.TestCase):
    def test_mob_stats(self):
        pve_service = PvEService()
        
        print("Testing Mob Stat Allocation (Level 5)...")
        level = 5
        difficulty = 1
        
        # Run multiple trials to see distribution
        for i in range(5):
            speed, resistance, hp_bonus, dmg_bonus = pve_service._allocate_mob_stats(level, difficulty)
            print(f"Trial {i+1}: Speed={speed}, Res={resistance}%, HP Bonus={hp_bonus}, DMG Bonus={dmg_bonus}")
            
            # Verify total points
            # hp: 20, dmg: 5, speed: 5, res: 5
            hp_pts = hp_bonus / 20
            dmg_pts = dmg_bonus / 5
            speed_pts = (speed - 10) / 5
            res_pts = resistance / 5
            
            total_pts = hp_pts + dmg_pts + speed_pts + res_pts
            # Allow small float precision errors
            self.assertAlmostEqual(total_pts, level, delta=0.1, msg=f"Expected {level} points, got {total_pts}")

    def test_boss_stats(self):
        pve_service = PvEService()
        print("\nTesting Boss Stat Allocation (Level 10)...")
        level = 10
        difficulty = 1
        for i in range(3):
            speed, resistance, hp_bonus, dmg_bonus = pve_service._allocate_mob_stats(level, difficulty, is_boss=True)
            print(f"Boss Trial {i+1}: Speed={speed}, Res={resistance}%, HP Bonus={hp_bonus}, DMG Bonus={dmg_bonus}")
            
            hp_pts = hp_bonus / 20
            dmg_pts = dmg_bonus / 5
            speed_pts = (speed - 20) / 5
            res_pts = resistance / 5
            
            total_pts = hp_pts + dmg_pts + speed_pts + res_pts
            self.assertAlmostEqual(total_pts, level, delta=0.1, msg=f"Expected {level} points, got {total_pts}")

if __name__ == "__main__":
    unittest.main()
