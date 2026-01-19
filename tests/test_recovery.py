import unittest
import datetime
from database import Database
from models.user import Utente
from services.user_service import UserService

class TestRecovery(unittest.TestCase):
    def setUp(self):
        self.db = Database()
        self.user_service = UserService()
        self.u1_id = 123456789
        
        # Clear and setup test user
        session = self.db.get_session()
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
        session.query(Utente).filter_by(id_telegram=self.u1_id).delete()
        session.commit()
        session.close()

    def test_restore_daily_health(self):
        """Verify 20% max HP restore per day"""
        session = self.db.get_session()
        user = session.query(Utente).filter_by(id_telegram=self.u1_id).first()
        
        # Initial: 50/100 HP. Restore 20% of 100 = 20 HP.
        # Note: restore_daily_health uses user.health (old field) in current implementation
        user.health = 50 
        session.commit()
        
        success, restored = self.user_service.restore_daily_health(user)
        self.assertTrue(success)
        self.assertEqual(restored, 20)
        
        session.refresh(user)
        self.assertEqual(user.health, 70)
        session.close()

    def test_restore_health_item(self):
        """Verify item-based health restoration"""
        session = self.db.get_session()
        user = session.query(Utente).filter_by(id_telegram=self.u1_id).first()
        
        # Restore 30 HP to 50 current_hp
        new_hp = self.user_service.restore_health(user, 30)
        self.assertEqual(new_hp, 80)
        
        session.refresh(user)
        self.assertEqual(user.current_hp, 80)
        session.close()

    def test_restore_mana_item(self):
        """Verify mana restoration"""
        session = self.db.get_session()
        user = session.query(Utente).filter_by(id_telegram=self.u1_id).first()
        
        # Restore 20 Mana to 50 mana (mana field is used for current mana in some places)
        # In models/user.py: mana=50, max_mana=50, current_mana=50
        # In user_service.py: restore_mana updates 'mana' field
        user.mana = 20
        session.commit()
        
        new_mana = self.user_service.restore_mana(user, 20)
        self.assertEqual(new_mana, 40)
        
        session.refresh(user)
        self.assertEqual(user.mana, 40)
        session.close()

    def test_use_mana(self):
        """Verify mana usage"""
        session = self.db.get_session()
        user = session.query(Utente).filter_by(id_telegram=self.u1_id).first()
        
        user.mana = 50
        session.commit()
        
        # Use 30 mana
        success = self.user_service.use_mana(user, 30)
        self.assertTrue(success)
        
        session.refresh(user)
        self.assertEqual(user.mana, 20)
        
        # Try to use 30 more (fail)
        success = self.user_service.use_mana(user, 30)
        self.assertFalse(success)
        session.close()

if __name__ == "__main__":
    unittest.main()
