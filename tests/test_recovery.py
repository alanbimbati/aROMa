import unittest
import datetime
import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from database import Database
from models.user import Utente
from services.user_service import UserService

from models.dungeon import DungeonParticipant

class TestRecovery(unittest.TestCase):
    def setUp(self):
        self.db = Database()
        self.user_service = UserService()
        self.u1_id = 123456789
        
        # Clear and setup test user
        session = self.db.get_session()
        # Clean dependencies first
        session.query(DungeonParticipant).filter_by(user_id=self.u1_id).delete()
        session.query(Utente).filter_by(id_telegram=self.u1_id).delete()
        
        self.user = Utente(
            id_telegram=self.u1_id,
            nome="TestUser",
            exp=0,
            livello=1,
            health=100,
            max_health=100,
            current_hp=50,
            mana=50,
            max_mana=50,
            current_mana=20,
            last_health_restore=datetime.datetime.now() - datetime.timedelta(days=2)
        )
        session.add(self.user)
        session.commit()
        session.close()

    def tearDown(self):
        # Clean up test user
        session = self.db.get_session()
        session.query(DungeonParticipant).filter_by(user_id=self.u1_id).delete()
        session.query(Utente).filter_by(id_telegram=self.u1_id).delete()
        session.commit()
        session.close()



    def test_restore_health_item(self):
        """Verify item-based health restoration"""
        session = self.db.get_session()
        user = session.query(Utente).filter_by(id_telegram=self.u1_id).first()
        
        # Restore 30 HP to 50 current_hp
        # restore_health returns amount restored
        restored = self.user_service.restore_health(user, 30)
        self.assertEqual(restored, 30)
        
        session.refresh(user)
        self.assertEqual(user.current_hp, 80)
        session.close()

    def test_restore_mana_item(self):
        """Verify mana restoration"""
        session = self.db.get_session()
        user = session.query(Utente).filter_by(id_telegram=self.u1_id).first()
        
        # Restore 20 Mana to 20 mana (set in setUp)
        # In setUp: current_mana=20
        # In test: user.mana = 20
        user.mana = 20
        session.commit()
        
        restored = self.user_service.restore_mana(user, 20)
        self.assertEqual(restored, 20)
        
        session.refresh(user)
        self.assertEqual(user.mana, 40)
        session.close()



if __name__ == "__main__":
    unittest.main()
