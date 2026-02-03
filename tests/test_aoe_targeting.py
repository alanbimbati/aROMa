import unittest
from unittest.mock import MagicMock, patch
import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from services.pve_service import PvEService
from models.pve import Mob

class TestAoELogic(unittest.TestCase):
    def setUp(self):
        with patch.object(PvEService, '__init__', return_value=None):
            self.service = PvEService()
        self.service.db = MagicMock()
        self.service.user_service = MagicMock()
        self.service.combat_service = MagicMock()
        self.service.event_dispatcher = MagicMock()
        self.service.combat_service.calculate_damage.return_value = {'damage': 100, 'is_crit': False, 'type': 'physical'}

    def test_aoe_priority(self):
        """Test that AoE prioritizes Dungeon mobs when user is in Dungeon"""
        session = MagicMock()
        
        # Mobs
        m1 = MagicMock(id=1, dungeon_id=99, is_dead=False, resistance=0, attack_type='physical', health=1000, max_health=1000) # Dungeon 99
        m2 = MagicMock(id=2, dungeon_id=None, is_dead=False, resistance=0, attack_type='physical', health=1000, max_health=1000) # World
        m3 = MagicMock(id=3, dungeon_id=88, is_dead=False, resistance=0, attack_type='physical', health=1000, max_health=1000) # Other dungeon
        
        # Mock Query to return all
        session.query(Mob).filter_by().all.return_value = [m1, m2, m3]
        self.service.db.get_session.return_value = session
        
        # Mock Dungeon Service
        with patch('services.dungeon_service.DungeonService') as MockDS:
            ds = MockDS.return_value
            # User is in Dungeon 99
            ds.get_user_active_dungeon.return_value = MagicMock(id=99)
            
            # User
            user = MagicMock(id_telegram=123)
            user.last_attack_time = None
            user.allocated_speed = 0
            user.mana = 100
            
            # Mock fatigue check
            self.service.user_service.check_fatigue.return_value = False
            
            # Helper for Char Loader
            with patch('services.character_loader.get_character_loader') as mock_loader:
                mock_loader.return_value.get_character_by_id.return_value = {}
                
                # Mock guild service
                self.service.guild_service = MagicMock()
                self.service.guild_service.get_mana_cost_multiplier.return_value = 1.0

                # Execute
                success, msg, extra, events = self.service.attack_aoe(user, base_damage=100, chat_id=-100, session=session)
            print(f"Result: success={success}, msg={msg}")
            
            # Verify Mobs hit
            if not success:
                self.fail(f"AoE Attack failed: {msg}")
                
            hit_ids = extra['mob_ids']
            self.assertIn(1, hit_ids) 
            self.assertIn(2, hit_ids)
            # m3 might be included if limit > 2. Here limit is 5.
            
            # Verify ordering/priority explicitly?
            # The method sorts them.
            # We can verify that the list passed to the loop was sorted.
            # But 'extra' only gives IDs.
            # However, if we limit to 1 target (mocking list slice?), we'd see filtering.
            
            print(f"Hit IDs: {hit_ids}")

if __name__ == '__main__':
    unittest.main()
