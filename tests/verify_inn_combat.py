import unittest
from unittest.mock import MagicMock, patch
from datetime import datetime
from services.pve_service import PvEService
from models.user import Utente

class TestInnCombat(unittest.TestCase):
    def setUp(self):
        self.pve_service = PvEService()
        self.pve_service.db = MagicMock()
        self.session = self.pve_service.db.get_session.return_value
        self.pve_service.user_service = MagicMock()
        
        # User in Resting state
        self.user = MagicMock(spec=Utente)
        self.user.id_telegram = 12345
        self.user.nome = "TestUser"
        self.user.resting_since = datetime.now()
        self.user.livello_selezionato = 1
        self.user.mana = 100
        self.user.health = 100
        self.user.max_health = 100
        self.user.max_mana = 100
        
    def test_attack_mob_blocked_when_resting(self):
        success, msg, extra = self.pve_service.attack_mob(self.user, chat_id=123, session=self.session)
        self.assertFalse(success)
        self.assertIn("Locanda", msg)
        
    def test_attack_aoe_blocked_when_resting(self):
        success, msg, extra, targets = self.pve_service.attack_aoe(self.user, chat_id=123, session=self.session)
        self.assertFalse(success)
        self.assertIn("Locanda", msg)
        
    def test_special_attack_blocked_when_resting(self):
        # Need character for special attack
        with patch('services.character_loader.get_character_loader') as mock_loader:
            mock_loader.return_value.get_character_by_id.return_value = {
                'id': 1, 'nome': 'Goku', 'special_attack_mana_cost': 10
            }
            success, msg, extra, targets = self.pve_service.use_special_attack(self.user, chat_id=123, session=self.session)
            self.assertFalse(success)
            self.assertIn("Locanda", msg)

if __name__ == '__main__':
    unittest.main()
