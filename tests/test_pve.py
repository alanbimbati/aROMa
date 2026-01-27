
import unittest
import sys
import os
import datetime

# Add project root to path
sys.path.append(os.getcwd())

from services.pve_service import PvEService
from models.user import Utente
from models.pve import Mob
from database import Database

class TestPvE(unittest.TestCase):
    def setUp(self):
        self.db = Database()
        self.session = self.db.get_session()
        self.pve_service = PvEService()
        
        self.chat_id = 210001
        self.user_id = 21001
        
        self.user = Utente(
            id_telegram=self.user_id, 
            nome="PvETester", 
            username="pvetester", 
            livello=10,
            health=1000,
            max_health=1000,
            base_damage=50
        )
        self.session.add(self.user)
        self.session.commit()
        
    def tearDown(self):
        self.session.query(Utente).filter_by(id_telegram=self.user_id).delete()
        self.session.query(Mob).filter_by(chat_id=self.chat_id).delete()
        self.session.commit()
        self.session.close()
        
    def test_spawn_mob(self):
        """Test spawning a mob"""
        success, msg, mob_id = self.pve_service.spawn_specific_mob(chat_id=self.chat_id)
        self.assertTrue(success)
        self.assertIsNotNone(mob_id)
        
        session = self.db.get_session()
        mob = session.query(Mob).filter_by(id=mob_id).first()
        self.assertIsNotNone(mob)
        self.assertEqual(mob.chat_id, self.chat_id)
        session.close()

    def test_attack_mob(self):
        """Test attacking a mob"""
        # Spawn
        self.pve_service.spawn_specific_mob(chat_id=self.chat_id)
        
        # Get mob ID
        session = self.db.get_session()
        mob = session.query(Mob).filter_by(chat_id=self.chat_id).first()
        mob_id = mob.id
        session.close()
        
        # Attack
        success, msg, _ = self.pve_service.attack_mob(self.user, 10)
        self.assertTrue(success)
        self.assertIn("Hai inflitto", msg)
        
        # Verify damage
        session = self.db.get_session()
        mob = session.query(Mob).filter_by(id=mob_id).first()
        self.assertLess(mob.health, mob.max_health)
        session.close()

    def test_kill_mob(self):
        """Test killing a mob"""
        # Spawn
        self.pve_service.spawn_specific_mob(chat_id=self.chat_id)
        
        # Attack
        success, msg, _ = self.pve_service.attack_mob(self.user, 1000) # Kill it
        self.assertTrue(success)
        print(f"Attack result: {msg}")
        
        # Verify dead
        session = self.db.get_session()
        mob = session.query(Mob).filter_by(chat_id=self.chat_id).first()
        self.assertTrue(mob.is_dead)
        session.close()
