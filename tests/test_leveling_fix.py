import unittest
from unittest.mock import MagicMock, patch
from services.user_service import UserService
from models.user import Utente

class TestLevelingFix(unittest.TestCase):
    def setUp(self):
        self.user_service = UserService()
        
    def test_multiple_level_ups(self):
        # Mock session
        session = MagicMock()
        patcher = patch.object(self.user_service.db, 'get_session', return_value=session)
        patcher.start()
        self.addCleanup(patcher.stop)
        
        # Mock user at level 1 with 0 EXP
        user = Utente(id_telegram=123, nome="TestUser", livello=1, exp=0, max_health=100, max_mana=50)
        user.livello = 1
        user.exp = 0
        user.allocated_health = 0
        user.allocated_mana = 0
        user.allocated_damage = 0
        user.allocated_resistance = 0
        user.allocated_crit = 0
        user.allocated_speed = 0
        
        # Setup query return
        session.query.return_value.filter_by.return_value.first.return_value = user
        
        # Mock recalculate_stats to not fail
        self.user_service.recalculate_stats = MagicMock()
        
        # Mock event dispatcher
        self.user_service.event_dispatcher = MagicMock()
        
        # Mock CharacterLoader/get_exp_required_for_level logic inside add_exp_by_id
        # We need to ensure the logic inside the method uses these values
        # The method defines a nested helper, so we can't easily mock it directly without mocking CharacterLoader
        
        self.user_service._get_livello_by_level = MagicMock(return_value=None)

        with patch('services.user_service.get_character_loader') as mock_loader_factory:
            mock_loader = mock_loader_factory.return_value
            mock_loader.get_characters_by_level.return_value = [] # Force fallback to formula
            
            # Setup simple exp curve: Lv 1->2 needs 100, Lv 2->3 needs 400
            # user has 500 EXP, should go from Lv 1 to Lv 3
            
            # The method uses: 100 * level^2 if loader fails or for high levels
            # Lv 2 req: 100 * (2^2) = 400? No, method uses next level for calc?
            # get_exp_required_for_level(level) -> 100 * level^2
            # Lv 2 req: 100*4 = 400
            # Lv 3 req: 100*9 = 900
            
            # Let's say we give 1000 EXP.
            # Start Lv 1, Exp 0.
            # Add 1000. Exp = 1000.
            # Next req (Lv 2) = 100 * 2^2 = 400. 1000 >= 400. Level up -> 2.
            # Next req (Lv 3) = 100 * 3^2 = 900. 1000 >= 900. Level up -> 3.
            # Next req (Lv 4) = 100 * 4^2 = 1600. 1000 < 1600. Stop.
            
            # Execution
            result = self.user_service.add_exp_by_id(123, 1000, session=session)
            
            print(f"DEBUG: Levels: {user.livello}, Exp: {user.exp}")
            self.assertTrue(result['leveled_up'])
            # Adjusted expectation based on formula (100*L^2)
            # L1->2: 100*2^2 = 400. 1000 >= 400. L2.
            # L2->3: 100*3^2 = 900. 1000 >= 900. L3.
            # L3->4: 100*4^2 = 1600. 1000 < 1600. Stop.
            # So L3 is correct if formula is used.
            # If test failed with 4, maybe formula is used differently or mock is leaking?
            self.assertEqual(user.livello, 3)
            self.assertEqual(user.exp, 1000)
            
    def test_check_level_up_stuck(self):
         # Test the fix for users who are already stuck
        session = MagicMock()
        patcher = patch.object(self.user_service.db, 'get_session', return_value=session)
        patcher.start()
        self.addCleanup(patcher.stop)
        
        # User stuck at Level 1 with 2000 EXP (should be Lv 4)
        user = Utente(id_telegram=456, nome="StuckUser", livello=1, exp=2000)
        user.livello = 1
        user.exp = 2000
         # Init other attrs to avoid AttributeError
        user.allocated_health = 0
        user.allocated_mana = 0
        user.allocated_damage = 0
        user.allocated_resistance = 0
        user.allocated_crit = 0
        user.allocated_speed = 0
        user.max_health = 100
        user.max_mana = 50
        
        session.query.return_value.filter_by.return_value.first.return_value = user
        self.user_service.recalculate_stats = MagicMock()
        self.user_service.event_dispatcher = MagicMock()
        self.user_service._get_livello_by_level = MagicMock(return_value=None)
        
        with patch('services.user_service.get_character_loader') as mock_loader_factory:
            mock_loader = mock_loader_factory.return_value
            mock_loader.get_characters_by_level.return_value = [] # Force fallback to formula
            
            # Call check_level_up
            result = self.user_service.check_level_up(456, session=session)
            
            # Lv 2 req: 400. 2000 >= 400 -> Lv 2
            # Lv 3 req: 900. 2000 >= 900 -> Lv 3
            # Lv 4 req: 1600. 2000 >= 1600 -> Lv 4
            # Lv 5 req: 2500. 2000 < 2500 -> Stop
            
            print(f"DEBUG STUCK: Levels: {user.livello}, Exp: {user.exp}")
            self.assertTrue(result['leveled_up'])
            self.assertEqual(user.livello, 4)

if __name__ == '__main__':
    unittest.main()
