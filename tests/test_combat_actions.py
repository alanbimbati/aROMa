import unittest
import os
import sys
import datetime
import random
import unittest.mock as mock

# Ensure we use the test database
os.environ['TEST_DB'] = '1'

# Add project root to path
sys.path.append(os.getcwd())

from database import Database
from models.user import Utente
from models.pve import Mob
from models.combat import CombatParticipation
from services.user_service import UserService
from services.pve_service import PvEService

class TestCombatActions(unittest.TestCase):
    def setUp(self):
        self.db = Database()
        self.session = self.db.get_session()
        self.user_service = UserService()
        self.pve_service = PvEService()
        self.user_id = 11223344
        self.chat_id = 999999
        
        # Cleanup
        self.session.query(Utente).filter_by(id_telegram=self.user_id).delete()
        self.session.query(Mob).filter_by(chat_id=self.chat_id).delete()
        self.session.query(CombatParticipation).filter_by(user_id=self.user_id).delete()
        self.session.commit()
        
        # Create user (Level 10 to have enough mana for special)
        # Set last_attack_time to far in the past to avoid cooldowns
        self.user = Utente(
            id_telegram=self.user_id,
            nome="CombatTester",
            health=100,
            max_health=100,
            current_hp=100,
            mana=100,
            max_mana=100,
            livello=10,
            livello_selezionato=1, # Crash Bandicoot
            last_attack_time=datetime.datetime.now() - datetime.timedelta(hours=1)
        )
        self.session.add(self.user)
        self.session.commit()

    def tearDown(self):
        self.session.query(Utente).filter_by(id_telegram=self.user_id).delete()
        self.session.query(Mob).filter_by(chat_id=self.chat_id).delete()
        self.session.commit()
        self.session.close()

    def test_attack_mob(self):
        """Test basic attack action"""
        mob = Mob(name="TestMob", health=100, max_health=100, attack_damage=10, chat_id=self.chat_id)
        self.session.add(mob)
        self.session.commit()
        
        user = self.session.query(Utente).filter_by(id_telegram=self.user_id).first()
        
        # Ensure no fatigue and no dungeon
        user.current_hp = 100
        self.session.commit()
        
        success, msg, extra = self.pve_service.attack_mob(user, base_damage=20, mob_id=mob.id)
        
        self.assertTrue(success, f"Attack failed: {msg}")
        self.assertIn("Hai inflitto", msg)
        
        self.session.refresh(mob)
        self.assertLess(mob.health, 100)

    def test_special_attack(self):
        """Test special attack action (consumes mana, returns 4 values)"""
        mob = Mob(name="TestMob", health=100, max_health=100, attack_damage=10, chat_id=self.chat_id)
        self.session.add(mob)
        self.session.commit()
        
        user = self.session.query(Utente).filter_by(id_telegram=self.user_id).first()
        initial_mana = user.mana
        
        # Ensure no fatigue and no dungeon
        user.current_hp = 100
        self.session.commit()
        
        # use_special_attack returns: success, msg, extra_data, attack_events
        result = self.pve_service.use_special_attack(user, chat_id=self.chat_id)
        self.assertEqual(len(result), 4, "use_special_attack should return 4 values")
        
        success, msg, extra_data, attack_events = result
        self.assertTrue(success, f"Special attack failed: {msg}")
        
        self.session.refresh(user)
        self.assertLess(user.mana, initial_mana)
        
        self.session.refresh(mob)
        self.assertLess(mob.health, 100)

    def test_attack_aoe(self):
        """Test AoE attack action"""
        # Spawn 3 mobs
        for i in range(3):
            mob = Mob(name=f"Mob{i}", health=50, max_health=50, attack_damage=5, chat_id=self.chat_id)
            self.session.add(mob)
        self.session.commit()
        
        user = self.session.query(Utente).filter_by(id_telegram=self.user_id).first()
        
        # Ensure no fatigue and no dungeon
        user.current_hp = 100
        self.session.commit()
        
        # attack_aoe returns: success, summary_msg, extra_data, attack_events
        success, msg, extra_data, attack_events = self.pve_service.attack_aoe(user, base_damage=30, chat_id=self.chat_id)
        
        self.assertTrue(success, f"AoE attack failed: {msg}")
        self.assertIn("ATTACCO AD AREA", msg)
        self.assertIn("mob_ids", extra_data)
        
        # Verify all mobs took damage
        mobs = self.session.query(Mob).filter_by(chat_id=self.chat_id).all()
        self.assertEqual(len(mobs), 3)
        for m in mobs:
            self.assertLess(m.health, 50)

    def test_flee_mob(self):
        """Test flee action"""
        mob1 = Mob(name="TestMob1", health=100, max_health=100, attack_damage=10, chat_id=self.chat_id, mob_level=1)
        mob2 = Mob(name="TestMob2", health=100, max_health=100, attack_damage=10, chat_id=self.chat_id, mob_level=1)
        self.session.add_all([mob1, mob2])
        self.session.commit()
        
        user = self.session.query(Utente).filter_by(id_telegram=self.user_id).first()
        
        with mock.patch('random.random', return_value=0.01): # Force success
            success, msg = self.pve_service.flee_mob(user, mob1.id)
            self.assertTrue(success, f"Flee success test failed: {msg}")
            self.assertIn("fuggito con successo", msg)
            
        with mock.patch('random.random', return_value=0.99): # Force failure
            success, msg = self.pve_service.flee_mob(user, mob2.id)
            self.assertFalse(success, "Flee failure test should return False")
            self.assertIn("rimasto bloccato", msg)

if __name__ == "__main__":
    unittest.main()
