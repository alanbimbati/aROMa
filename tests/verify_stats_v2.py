import sys
import os
from unittest.mock import MagicMock, patch

# Add project root to path
sys.path.append('/home/alan/Documenti/Coding/aroma')

from services.user_service import UserService
from services.character_loader import get_character_loader

def test_stat_formula_refactoring():
    print("Testing Stat Formula Refactoring...")
    
    # We mock out EquipmentService to avoid DB queries
    with patch('services.user_service.EquipmentService') as MockEquipService:
        mock_equip = MockEquipService.return_value
        mock_equip.calculate_equipment_stats.return_value = {} # No gear for this test
        
        us = UserService()
        
        # Mock user at level 10 with 50 allocated health points
        # Level 10 should give:
        # System Base: 20 HP, 20 Mana, 5 DMG
        # Level Scaling: (10-1)*2 = +18 HP, (10-1)*1 = +9 Mana, (10-1)*0.5 = +4.5 DMG
        # Total System: 38 HP, 29 Mana, 9.5 DMG
        
        user = MagicMock()
        user.id_telegram = 123456789
        user.livello = 10
        user.livello_selezionato = 1 # Chocobo
        user.allocated_health = 50 # +500 HP
        user.allocated_mana = 0
        user.allocated_damage = 0
        user.allocated_resistance = 0
        user.allocated_crit = 0
        user.allocated_speed = 0
        
        # Chocobo (id 1) stats from CSV:
        # bonus_health: 10
        # speed: 51
        # crit_chance: 5
        
        stats = us.get_projected_stats(user)
        
        print(f"Projected Stats for Chocobo Lv 10 (+50 Health Alloc):")
        print(f"HP: {stats['max_health']}")
        print(f"Mana: {stats['max_mana']}")
        print(f"Damage: {stats['base_damage']}")
        print(f"Speed: {stats['speed']}")
        print(f"Crit: {stats['crit_chance']}%")
        
        # Expected HP: 38 (system) + 10 (char bonus) + 500 (alloc) = 548
        # Expected Mana: 29 (system) + 0 (char bonus) + 0 (alloc) = 29
        # Expected DMG: 9.5 (system) -> 9 + 0 (char bonus) + 0 (alloc) = 9
        
        assert stats['max_health'] == 548
        assert stats['max_mana'] == 29
        assert stats['base_damage'] == 9
        assert stats['speed'] == 51
        assert stats['crit_chance'] == 5
        
        print("\n--- Level 1 Test ---")
        user.livello = 1
        user.allocated_health = 0
        stats_lv1 = us.get_projected_stats(user)
        # HP: 20 (base) + 0 (scaling) + 10 (char bonus) = 30
        assert stats_lv1['max_health'] == 30
        print(f"Lv 1 Chocobo HP: {stats_lv1['max_health']} (Matches 20 base + 10 character)")
        
        print("✅ Stat Formula Refactoring Verified")

if __name__ == "__main__":
    test_stat_formula_refactoring()
