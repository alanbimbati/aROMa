
import unittest
import sys
import os
import datetime

# Add project root to path
sys.path.append(os.getcwd())

from services.dungeon_service import DungeonService
from models.user import Utente
from models.dungeon import Dungeon, DungeonParticipant
from models.pve import Mob
from models.combat import CombatParticipation
from database import Database

class TestDungeonSpawn(unittest.TestCase):
    def setUp(self):
        self.db = Database()
        self.session = self.db.get_session()
        self.dungeon_service = DungeonService()
        self.chat_id = 888888
        self.user_id = 12345
        
        # Cleanup
        self.session.query(CombatParticipation).delete()
        self.session.query(DungeonParticipant).delete()
        self.session.query(Mob).filter_by(chat_id=self.chat_id).delete()
        self.session.query(Dungeon).filter_by(chat_id=self.chat_id).delete()
        self.session.query(Utente).filter_by(id_telegram=self.user_id).delete()
        self.session.commit()
        
        # Create test user
        user = Utente(id_telegram=self.user_id, username="testuser", nome="Test User")
        self.session.add(user)
        self.session.commit()

    def tearDown(self):
        self.session.query(CombatParticipation).delete()
        self.session.query(DungeonParticipant).delete()
        self.session.query(Mob).filter_by(chat_id=self.chat_id).delete()
        self.session.query(Dungeon).filter_by(chat_id=self.chat_id).delete()
        self.session.query(Utente).filter_by(id_telegram=self.user_id).delete()
        self.session.commit()
        self.session.close()

    def test_start_dungeon_spawns_mobs(self):
        """Test that starting a dungeon spawns the first stage mobs"""
        # 1. Create dungeon registration
        d_id, msg = self.dungeon_service.create_dungeon(self.chat_id, 1, self.user_id)
        self.assertIsNotNone(d_id)
        
        # 2. Start dungeon
        success, msg, events = self.dungeon_service.start_dungeon(self.chat_id)
        self.assertTrue(success)
        
        # 3. Verify mobs in DB
        mobs = self.session.query(Mob).filter_by(dungeon_id=d_id, is_dead=False).all()
        self.assertGreater(len(mobs), 0, "No mobs found in DB for the started dungeon")
        
        # 4. Verify events contain spawn
        spawn_event = next((e for e in events if e['type'] == 'spawn'), None)
        self.assertIsNotNone(spawn_event, "No spawn event returned by start_dungeon")
        self.assertIn('mob_ids', spawn_event)
        self.assertEqual(len(spawn_event['mob_ids']), len(mobs))

if __name__ == '__main__':
    unittest.main()
