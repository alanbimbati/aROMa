import unittest
from unittest.mock import MagicMock, patch
from services.boot_service import BootService
from models.user import Utente

class TestBootService(unittest.TestCase):
    def setUp(self):
        self.boot_service = BootService()
        self.boot_service.db = MagicMock()
        self.boot_service.user_service = MagicMock()
        self.boot_service.leveling_service = MagicMock()

    @patch('services.boot_service.init_database')
    @patch('services.achievement_tracker.AchievementTracker')
    def test_run_startup_sequence(self, MockTracker, mock_init_db):
        mock_bot = MagicMock()
        self.boot_service.startup_and_clean = MagicMock()
        
        self.boot_service.run_startup_sequence(mock_bot)
        
        mock_init_db.assert_called_once()
        MockTracker.return_value.load_from_csv.assert_called_once()
        MockTracker.return_value.load_from_json.assert_called_once()
        self.boot_service.startup_and_clean.assert_called_once()

    def test_startup_and_clean(self):
        session = MagicMock()
        self.boot_service.db.get_session.return_value = session
        
        # We need mock query chain
        mock_query = session.query.return_value
        
        user1 = Utente(id_telegram=1, exp=None, livello=None)
        user2 = Utente(id_telegram=2, exp=100, livello=2)
        mock_query.all.return_value = [user1, user2]
        
        self.boot_service.startup_and_clean()
        
        # Verify Fallback logic
        self.assertEqual(user1.exp, 0)
        self.assertEqual(user1.livello, 1)
        self.assertEqual(user1.allocated_health, 0)
        
        # Verify recalculations called for both users
        self.assertEqual(self.boot_service.leveling_service.recalculate_level.call_count, 2)
        self.assertEqual(self.boot_service.user_service.recalculate_stats.call_count, 2)
        
        session.commit.assert_called_once()
        session.close.assert_called_once()

if __name__ == '__main__':
    unittest.main()
