
import unittest
import sys
import os
import datetime
os.environ['TEST_DB'] = '1'

# Add project root to path
sys.path.append(os.getcwd())

from services.dungeon_service import DungeonService
from services.pve_service import PvEService
from models.dungeon import Dungeon, DungeonParticipant
from models.pve import Mob
from models.user import Utente
from database import Database

class TestDungeonAdvancement(unittest.TestCase):
    def setUp(self):
        self.db = Database()
        self.session = self.db.get_session()
        self.dungeon_service = DungeonService()
        self.pve_service = PvEService()
        self.chat_id = 777777
        self.user_id = 54321
        
        # Cleanup
        self.session.query(Dungeon).filter_by(chat_id=self.chat_id).delete()
        self.session.query(Mob).filter_by(chat_id=self.chat_id).delete()
        self.session.query(Utente).filter_by(id_telegram=self.user_id).delete()
        self.session.commit()
        
        # Create user
        self.user = Utente(id_telegram=self.user_id, nome="TestUser", health=100, max_health=100, mana=100, max_mana=100, livello=10)
        self.session.add(self.user)
        self.session.commit()

    def tearDown(self):
        self.session.query(Dungeon).filter_by(chat_id=self.chat_id).delete()
        self.session.query(Mob).filter_by(chat_id=self.chat_id).delete()
        self.session.query(Utente).filter_by(id_telegram=self.user_id).delete()
        self.session.commit()
        self.session.close()

    def test_aoe_kill_advances_dungeon(self):
        """Test that killing all mobs in a step with AoE advances the dungeon"""
        # 1. Create dungeon registration
        d_id, msg = self.dungeon_service.create_dungeon(self.chat_id, 1, self.user_id)
        self.assertIsNotNone(d_id)
        
        # 2. Start dungeon (spawns 3 saibaman)
        success, msg, events = self.dungeon_service.start_dungeon(self.chat_id)
        self.assertTrue(success)
        
        # 3. Verify mobs exist
        mobs = self.session.query(Mob).filter_by(dungeon_id=d_id, is_dead=False).all()
        self.assertEqual(len(mobs), 3)
        
        # 4. Perform AoE attack that kills them all
        # We'll set their health to 1 to ensure they die
        for mob in mobs:
            mob.health = 1
        self.session.commit()
        
        # Refresh user from session
        user = self.session.query(Utente).filter_by(id_telegram=self.user_id).first()
        
        success, msg, extra_data, attack_events = self.pve_service.attack_aoe(user, base_damage=100, chat_id=self.chat_id)
        self.assertTrue(success)
        
        # 5. Verify dungeon advanced
        self.session.expire_all()
        dungeon = self.session.query(Dungeon).filter_by(id=d_id).first()
        self.assertEqual(dungeon.current_stage, 2, "Dungeon did not advance to stage 2 after AoE kill")
        
        # 6. Verify new mobs/boss spawned
        new_mobs = self.session.query(Mob).filter_by(dungeon_id=d_id, is_dead=False).all()
        self.assertGreater(len(new_mobs), 0, "No new mobs spawned for stage 2")
        
        # 7. Verify extra_data contains dungeon_events
        self.assertIn('dungeon_events', extra_data, "extra_data missing dungeon_events")

if __name__ == '__main__':
    unittest.main()
