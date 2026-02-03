
import unittest
import sys
import os
import datetime
os.environ['TEST_DB'] = '1'

# Add project root to path
sys.path.append(os.getcwd())

from services.pve_service import PvEService
from models.dungeon import Dungeon, DungeonParticipant
from models.pve import Mob
from models.user import Utente
from database import Database

class TestNameError(unittest.TestCase):
    def setUp(self):
        self.db = Database()
        self.session = self.db.get_session()
        self.pve_service = PvEService()
        self.chat_id = 666666
        self.user_id = 66666
        
        # Cleanup
        self.session.query(Dungeon).filter_by(chat_id=self.chat_id).delete()
        self.session.query(Mob).filter_by(chat_id=self.chat_id).delete()
        self.session.query(Utente).filter_by(id_telegram=self.user_id).delete()
        self.session.commit()
        
        # Create user
        self.user = Utente(id_telegram=self.user_id, nome="TestUser", health=100, max_health=100, mana=100, max_mana=100, livello=10)
        self.session.add(self.user)
        
        # Create dungeon
        self.dungeon = Dungeon(name="TestDungeon", chat_id=self.chat_id, dungeon_def_id=1, status="active")
        self.session.add(self.dungeon)
        self.session.commit()
        
        # Add participant
        self.part = DungeonParticipant(dungeon_id=self.dungeon.id, user_id=self.user_id)
        self.session.add(self.part)
        
        # Create dungeon mob
        self.mob = Mob(name="TestMob", health=100, max_health=100, attack_damage=10, chat_id=self.chat_id, dungeon_id=self.dungeon.id)
        self.session.add(self.mob)
        self.session.commit()

    def tearDown(self):
        from models.combat import CombatParticipation
        self.session.rollback()
        
        from sqlalchemy import text
        try:
            self.session.execute(text("TRUNCATE dungeon_participant CASCADE"))
            self.session.execute(text("TRUNCATE combat_participation CASCADE"))
        except:
            pass
        self.session.commit()
        
        self.session.query(Mob).filter_by(chat_id=self.chat_id).delete()
        self.session.query(Dungeon).filter_by(chat_id=self.chat_id).delete()
        self.session.query(Utente).filter_by(id_telegram=self.user_id).delete()
        self.session.commit()
        self.session.close()

    def test_attack_no_kill_no_error(self):
        """Test that attacking a dungeon mob without killing it doesn't raise NameError"""
        user = self.session.query(Utente).filter_by(id_telegram=self.user_id).first()
        mob = self.session.query(Mob).filter_by(chat_id=self.chat_id).first()
        
        # This should NOT raise NameError
        try:
            success, msg, extra_data = self.pve_service.attack_mob(user, base_damage=10, mob_id=mob.id, session=self.session)
            self.assertTrue(success)
        except NameError as e:
            self.fail(f"attack_mob raised NameError: {e}")

if __name__ == '__main__':
    unittest.main()
