import unittest
from unittest.mock import MagicMock, patch
import datetime
from services.guild_service import GuildService
from services.potion_service import PotionService

class TestGuildBonuses(unittest.TestCase):
    
    def setUp(self):
        self.mock_db = MagicMock()
        self.mock_session = MagicMock()
        self.mock_db.get_session.return_value = self.mock_session
        
        # Patch Database to return our mock
        self.db_patcher = patch('services.guild_service.Database', return_value=self.mock_db)
        self.db_patcher.start()
        
        self.guild_service = GuildService()
        self.guild_service.db = self.mock_db # Ensure it uses our mock
        
        # Determine base multipliers
        # Default potion bonus is 15% (Lv 1 Brewery is default if not set)
        
    def tearDown(self):
        self.db_patcher.stop()

    def test_brothel_mana_reduction(self):
        """Test that Vigore buff reduces mana cost correctly"""
        user_id = 12345
        
        # Mock User
        mock_user = MagicMock()
        self.mock_session.query.return_value.filter_by.return_value.first.return_value = mock_user
        
        # Case 1: Vigore Active
        mock_user.vigore_until = datetime.datetime.now() + datetime.timedelta(minutes=30)
        multiplier = self.guild_service.get_mana_cost_multiplier(user_id)
        self.assertEqual(multiplier, 0.5, "Multiplier should be 0.5 when Vigore is active")
        
        # Case 2: Vigore Expired
        mock_user.vigore_until = datetime.datetime.now() - datetime.timedelta(minutes=1)
        multiplier = self.guild_service.get_mana_cost_multiplier(user_id)
        self.assertEqual(multiplier, 1.0, "Multiplier should be 1.0 when Vigore is expired")
        
        # Case 3: No Vigore
        mock_user.vigore_until = None
        multiplier = self.guild_service.get_mana_cost_multiplier(user_id)
        self.assertEqual(multiplier, 1.0, "Multiplier should be 1.0 when Vigore is None")

    def test_brewery_potion_bonus_calculation(self):
        """Test calculation of beer bonus based on brewery level"""
        user_id = 12345
        
        # Mock Guild logic inside get_user_guild
        # We need to mock get_user_guild to return a dict with brewery_level
        
        # Case 1: No Guild -> 1.0 (no bonus? Actually get_potion_bonus currently requires guild? No, let's see code)
        with patch.object(self.guild_service, 'get_user_guild', return_value=None):
            bonus = self.guild_service.get_potion_bonus(user_id)
            self.assertEqual(bonus, 1.0, "Should be 1.0 (no bonus) if not in guild")
            
        # Case 2: Guild with Brewery Lv 1
        # Formula: 1.0 + (15 + (Lv*5))/100 = 1.0 + 0.20 = 1.20
        with patch.object(self.guild_service, 'get_user_guild', return_value={'brewery_level': 1, 'inn_level': 1}):
            bonus = self.guild_service.get_potion_bonus(user_id)
            self.assertEqual(bonus, 1.20, "Lv 1 Brewery should give +20% (1.20)")
            
        # Case 3: Brewery Lv 5
        # Formula: 15 + 25 = 40% -> 1.40
        with patch.object(self.guild_service, 'get_user_guild', return_value={'brewery_level': 5, 'inn_level': 1}):
            bonus = self.guild_service.get_potion_bonus(user_id)
            self.assertEqual(bonus, 1.40, "Lv 5 Brewery should give +40% (1.40)")

    @patch('services.potion_service.Database')
    @patch('services.potion_service.UserService')
    def test_apply_potion_bonus(self, MockUserService, MockDB):
        """Test that the potion service actually applies the bonus"""
        mock_user_service = MockUserService.return_value
        potion_service = PotionService()
        potion_service.user_service = mock_user_service
        potion_service.db = self.mock_db
        
        user = MagicMock()
        user.id_telegram = 12345
        user.premium = 0
        
        # Mock potion data
        potion_name = "Pozione Media"
        potion_data = {'nome': 'Pozione Media', 'tipo': 'health_potion', 'effetto_valore': 100, 'prezzo': 10}
        
        potion_service.potions = [potion_data]
        
        # Mock GuildService.get_potion_bonus to return 1.5 (+50%)
        # We need to patch the GuildService instantiated INSIDE apply_potion_effect
        with patch('services.guild_service.GuildService.get_potion_bonus', return_value=1.5):
            potion_service.apply_potion_effect(user, potion_name)
            
            # Check calling arguments for restore_health
            # Original value 100 * 1.5 = 150
            mock_user_service.restore_health.assert_called_with(user, 150, session=None)
            
if __name__ == '__main__':
    unittest.main()
