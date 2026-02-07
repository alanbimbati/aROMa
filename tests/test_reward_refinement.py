import unittest
from unittest.mock import MagicMock, patch
from services.reward_service import RewardService
from models.user import Utente

class TestRewardLogicRefinement(unittest.TestCase):
    def setUp(self):
        self.db = MagicMock()
        self.user_service = MagicMock()
        self.item_service = MagicMock()
        self.season_manager = MagicMock()
        self.reward_service = RewardService(self.db, self.user_service, self.item_service, self.season_manager)
        self.reward_service.crafting_service = MagicMock()
        
        # Mock item loading
        self.item_service.load_items_from_csv.return_value = [
            {'nome': 'Pozione', 'rarita': 100}
        ]
        
        # Mocking generic mob
        self.mob = MagicMock()
        self.mob.difficulty_tier = 1
        self.mob.is_boss = False

    def test_reward_distribution_fled(self):
        """Verify that fled players receive no rewards"""
        # Participant who fled
        p_fled = MagicMock()
        p_fled.user_id = 123
        p_fled.damage_dealt = 100
        p_fled.has_fled = True
        
        rewards_data = self.reward_service.calculate_rewards(self.mob, [p_fled])
        self.assertTrue(rewards_data[0]['has_fled'])
        
        # Distribution
        session = MagicMock()
        user = Utente(id_telegram=123, current_hp=100, health=100, max_health=100, game_name="Fuggitivo")
        session.query().filter_by().first.return_value = user
        
        summary = self.reward_service.distribute_rewards(rewards_data, self.mob, session)
        
        # Verify no rewards applied
        self.user_service.add_exp_by_id.assert_called_with(123, 0, session=session)
        self.user_service.add_points_by_id.assert_called_with(123, 0, is_drop=True, session=session)
        self.assertIn("(Fuggito)", summary)
        self.assertIn("0 Exp, 0", summary)

    def test_reward_distribution_dead(self):
        """Verify that dead players receive Wumpa but no EXP"""
        # Participant who died
        p_dead = MagicMock()
        p_dead.user_id = 456
        p_dead.damage_dealt = 100
        p_dead.has_fled = False
        
        rewards_data = self.reward_service.calculate_rewards(self.mob, [p_dead])
        
        # Distribution
        session = MagicMock()
        user = Utente(id_telegram=456, current_hp=0, health=100, max_health=100, game_name="Caduto")
        session.query().filter_by().first.return_value = user
        
        # Mock add_exp_by_id to return leveled_up info
        self.user_service.add_exp_by_id.return_value = {'leveled_up': False}
        
        summary = self.reward_service.distribute_rewards(rewards_data, self.mob, session)
        
        # Verify EXP is 0 but Wumpa is > 0
        self.user_service.add_exp_by_id.assert_called_with(456, 0, session=session)
        
        # Check that add_points_by_id was called with something > 0
        args, kwargs = self.user_service.add_points_by_id.call_args
        wumpa_awarded = args[1]
        self.assertGreater(wumpa_awarded, 0)
        
        self.assertIn("(Morto)", summary)
        self.assertIn("0 Exp", summary)
        self.assertRegex(summary, r"[1-9]\d* [^0]") # Should have some points

if __name__ == '__main__':
    unittest.main()
