
import unittest
from unittest.mock import MagicMock, patch
from services.pve_service import PvEService
from services.item_service import ItemService
from models.user import Utente
from models.pve import Mob
import datetime
import json

class TestNitroTNT(unittest.TestCase):
    def setUp(self):
        self.pve_service = PvEService()
        self.item_service = ItemService()
        self.pve_service.db = MagicMock()
        self.item_service.db = MagicMock()
        self.pve_service.user_service = MagicMock()
        self.item_service.user_service = MagicMock()
        
    def test_nitro_on_mob(self):
        # Mock user and mob
        user = Utente(id_telegram=123, nome="Hero", points=100)
        mob = Mob(id=1, name="Goblin", health=1000, max_health=1000)
        
        # Test apply_effect
        msg, data = self.item_service.apply_effect(user, "Nitro", target_mob=mob)
        
        self.assertIn("Hai lanciato Nitro contro Goblin", msg)
        self.assertEqual(data['type'], 'mob_drop')
        self.assertEqual(data['percent'], 0.15)
        self.assertEqual(data['damage'], 100) # 10% of 1000
        
    def test_nitro_next_mob_effect(self):
        # Mock user
        user = Utente(id_telegram=123, nome="Hero")
        
        # Test apply_effect without target
        msg, data = self.item_service.apply_effect(user, "Nitro")
        
        self.assertEqual(data['type'], 'nitro_trap')
        
    def test_apply_pending_effects(self):
        # Setup pending effect
        chat_id = 456
        self.pve_service.pending_mob_effects[chat_id] = ['Nitro']
        
        # Mock mob in DB
        mob = Mob(id=1, name="Goblin", health=1000, max_health=1000)
        session = MagicMock()
        self.pve_service.db.get_session.return_value = session
        session.query.return_value.filter_by.return_value.first.return_value = mob
        
        # Apply pending
        applied = self.pve_service.apply_pending_effects(1, chat_id, session=session)
        
        self.assertEqual(len(applied), 1)
        self.assertEqual(applied[0]['effect'], 'Nitro')
        self.assertEqual(applied[0]['damage'], 100)
        self.assertEqual(mob.health, 900)
        self.assertEqual(self.pve_service.pending_mob_effects[chat_id], [])

if __name__ == '__main__':
    unittest.main()
