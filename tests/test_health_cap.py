import unittest
import datetime
import os
os.environ['TEST_DB'] = '1'
from database import Database
from models.user import Utente
from models.pve import Mob
from services.user_service import UserService
from services.pve_service import PvEService

class TestHealthCap(unittest.TestCase):
    def setUp(self):
        self.db = Database()
        self.user_service = UserService()
        self.pve_service = PvEService()
        self.u1_id = 999888777
        
        # Clear and setup test user
        session = self.db.get_session()
        session.query(Utente).filter_by(id_telegram=self.u1_id).delete()
        
        self.user = Utente(
            id_telegram=self.u1_id,
            nome="CapTestUser",
            exp=0,
            livello=1,
            health=9999,
            max_health=100,
            current_hp=9999,
            mana=50,
            max_mana=50,
            current_mana=50
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

    def test_damage_caps_health(self):
        """Test that taking damage when HP > Max HP results in HP = Max HP - Damage"""
        session = self.db.get_session()
        user = session.query(Utente).filter_by(id_telegram=self.u1_id).first()
        
        # Take 10 damage. Expected: 100 - 10 = 90
        new_hp, died = self.user_service.damage_health(user, 10)
        
        self.assertEqual(new_hp, 90)
        self.assertFalse(died)
        
        session.refresh(user)
        self.assertEqual(user.current_hp, 90)
        self.assertEqual(user.health, 90)
        session.close()

    def test_restore_caps_health(self):
        """Test that restoring health when HP > Max HP results in HP = Max HP"""
        session = self.db.get_session()
        user = session.query(Utente).filter_by(id_telegram=self.u1_id).first()
        
        # Restore 10 HP. Expected: 100 (since it was 9999)
        restored = self.user_service.restore_health(user, 10)
        
        # Since current_hp (9999) >= max_hp (100), it should probably return 0 restored but fix the cap
        # Or if we want it to be more robust, it should fix the cap anyway.
        
        session.refresh(user)
        self.assertEqual(user.current_hp, 100)
        self.assertEqual(user.health, 100)
        session.close()

    def test_recalculate_caps_health(self):
        """Test that recalculate_stats correctly caps HP"""
        self.user_service.recalculate_stats(self.u1_id)
        
        session = self.db.get_session()
        user = session.query(Utente).filter_by(id_telegram=self.u1_id).first()
        
        # Base HP for lvl 1 is 100 + (1 * 5) = 105
        self.assertEqual(user.max_health, 105)
        self.assertEqual(user.current_hp, 105)
        self.assertEqual(user.health, 105)
        session.close()

    def test_kill_regen_caps_health(self):
        """Test that killing a mob with HP > Max HP results in HP = Max HP"""
        session = self.db.get_session()
        user = session.query(Utente).filter_by(id_telegram=self.u1_id).first()
        
        # Create a mob to kill
        mob = Mob(name="TestMob", health=1, max_health=1, attack_damage=1, chat_id=123)
        session.add(mob)
        session.commit()
        mob_id = mob.id
        
        # Mock attack to kill mob
        # We need to bypass cooldowns etc. for simplicity or just use the service
        # Let's use attack_mob
        success, msg, extra = self.pve_service.attack_mob(user, base_damage=10, mob_id=mob_id)
        
        # Refresh user to see changes from attack_mob (which uses its own sessions)
        session.refresh(user)
        
        self.assertTrue(success)
        self.assertIn("sconfitto", msg)
        
        session.refresh(user)
        # Should be max_health (105 due to lvl 1 growth)
        self.assertEqual(user.current_hp, user.max_health)
        self.assertEqual(user.health, user.max_health)
        
        # Clean up mob
        session.query(Mob).filter_by(id=mob_id).delete()
        session.commit()
        session.close()

if __name__ == "__main__":
    unittest.main()
