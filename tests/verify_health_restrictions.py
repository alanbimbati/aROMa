import unittest
from unittest.mock import MagicMock, patch
from services.pve_service import PvEService
from models.user import Utente
from models.pve import Mob
from datetime import datetime, timedelta

class TestCombatHealthRestrictions(unittest.TestCase):
    def setUp(self):
        self.pve_service = PvEService()
        self.pve_service.db = MagicMock()
        self.pve_service.user_service = MagicMock()
        self.pve_service.guild_service = MagicMock()
        
        # Mock user
        self.user = Utente(id_telegram=123, nome="TestUser", livello=10)
        self.user.max_health = 100
        self.user.health = 100
        self.user.current_hp = 100
        self.user.mana = 100
        self.user.max_mana = 100
        self.user.livello_selezionato = 1 # Goku
        self.user.resting_since = None
        self.user.meditating_until = None
        self.user.last_attack_time = None
        
        # Mock mob
        self.mob = Mob(id=1, name="Saibaman", health=100, max_health=100, is_dead=False, chat_id=456)
        
    def test_attack_blocked_when_dead(self):
        self.user.current_hp = 0
        self.user.health = 0
        
        success, msg, extra = self.pve_service.attack_mob(self.user, chat_id=456)
        
        self.assertFalse(success)
        self.assertIn("Sei morto", msg)
        
    def test_attack_blocked_when_fatigued(self):
        self.user.current_hp = 4 # 4%
        self.user.health = 4
        
        success, msg, extra = self.pve_service.attack_mob(self.user, chat_id=456)
        
        self.assertFalse(success)
        self.assertIn("troppo stanco", msg)
        
    def test_defend_blocked_when_dead(self):
        self.user.current_hp = 0
        self.user.health = 0
        
        # We need to mock session for defend
        mock_session = MagicMock()
        mock_session.merge.return_value = self.user
        mock_session.query().filter_by().first.return_value = self.mob
        self.pve_service.db.get_session.return_value = mock_session
        
        success, msg, extra = self.pve_service.defend(self.user, chat_id=456)
        
        self.assertFalse(success)
        self.assertIn("Sei morto", msg)
        
    def test_defend_allowed_when_fatigued(self):
        self.user.current_hp = 4 # 4%
        self.user.health = 4
        
        # Mock session for defend
        mock_session = MagicMock()
        mock_session.merge.return_value = self.user
        mock_session.query().filter_by().first.return_value = self.mob
        self.pve_service.db.get_session.return_value = mock_session
        
        # Mock parry service
        self.pve_service.parry_service = MagicMock()
        self.pve_service.parry_service.activate_parry.return_value = {
            'success': True,
            'parry_id': 1,
            'window_duration': 2.5,
            'expires_at': datetime.now() + timedelta(seconds=2.5)
        }
        
        # Mock status effect
        with patch('services.status_effects.StatusEffect.apply_status'):
            success, msg, extra = self.pve_service.defend(self.user, chat_id=456)
            
            # Should not be blocked by HP check (only dead is blocked)
            # It might fail due to cooldown if not careful, but setUp has no last_attack_time
            self.assertTrue(success, f"Failed with: {msg}")

    def test_special_attack_blocked_when_dead(self):
        self.user.current_hp = 0
        self.user.health = 0
        
        success, msg, extra, rewards = self.pve_service.use_special_attack(self.user, chat_id=456)
        
        self.assertFalse(success)
        self.assertIn("Sei morto", msg)

    def test_special_attack_blocked_when_fatigued(self):
        self.user.current_hp = 4 # 4%
        self.user.health = 4
        
        success, msg, extra, rewards = self.pve_service.use_special_attack(self.user, chat_id=456)
        
        self.assertFalse(success)
        self.assertIn("troppo stanco", msg)

if __name__ == '__main__':
    unittest.main()
