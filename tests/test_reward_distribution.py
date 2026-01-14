import unittest
from database import Database
from models.user import Utente
from models.pve import Mob
from models.combat import CombatParticipation
from models.dungeon import Dungeon
from services.user_service import UserService
from services.pve_service import PvEService
import datetime

class TestRewardDistribution(unittest.TestCase):
    def setUp(self):
        self.db = Database()
        self.user_service = UserService()
        self.pve_service = PvEService()
        
        # Create test users
        session = self.db.get_session()
        def get_or_create(uid, username, nome):
            u = session.query(Utente).filter_by(id_telegram=uid).first()
            if not u:
                u = Utente(id_telegram=uid, username=username, nome=nome, points=0, exp=0, game_name=nome)
                session.add(u)
            u.game_name = nome
            u.points = 0
            u.exp = 0
            u.current_hp = 100
            u.max_health = 100
            u.last_attack_time = datetime.datetime.now() - datetime.timedelta(hours=1)
            return u

        self.u1_id = 12345
        self.u2_id = 67890
        get_or_create(self.u1_id, "user1", "Alan Bimbati")
        get_or_create(self.u2_id, "user2", "Viktor")
        session.commit()
        session.close()

    def tearDown(self):
        session = self.db.get_session()
        session.query(Mob).filter_by(chat_id=888).delete()
        session.query(CombatParticipation).delete()
        session.commit()
        session.close()

    def test_multi_user_rewards(self):
        """Verify that multiple users get rewards based on damage"""
        # Spawn a mob
        success, msg, mob_id = self.pve_service.spawn_specific_mob(chat_id=888)
        self.assertTrue(success)
        
        session = self.db.get_session()
        mob = session.query(Mob).filter_by(id=mob_id).first()
        mob.health = 300
        mob.max_health = 300
        session.commit()
        
        u1 = session.query(Utente).filter_by(id_telegram=self.u1_id).first()
        u2 = session.query(Utente).filter_by(id_telegram=self.u2_id).first()
        session.close() # CLOSE BEFORE SERVICE CALL
        
        # User 1 attacks
        success, msg = self.pve_service.attack_mob(u1, base_damage=200, mob_id=mob_id)
        self.assertTrue(success)
        self.assertIn("Hai inflitto", msg)
        self.assertNotIn("sconfitto", msg)
        
        # User 2 attacks (kills it)
        success, msg = self.pve_service.attack_mob(u2, base_damage=500, mob_id=mob_id)
        self.assertTrue(success)
        self.assertIn("sconfitto", msg)
        
        # Check message content
        print(f"DEBUG: Kill Message:\n{msg}")
        self.assertIn("Alan Bimbati", msg)
        self.assertIn("Viktor", msg)
        self.assertIn("Ricompense Distribuite", msg)
        # Check for the new ratio format [Damage]/[Max HP]
        self.assertIn("/300 dmg", msg) 
        
        # Verify database updates
        session = self.db.get_session()
        u1_after = session.query(Utente).filter_by(id_telegram=self.u1_id).first()
        u2_after = session.query(Utente).filter_by(id_telegram=self.u2_id).first()
        
        print(f"DEBUG: User 1 Points: {u1_after.points}, Exp: {u1_after.exp}")
        print(f"DEBUG: User 2 Points: {u2_after.points}, Exp: {u2_after.exp}")
        
        self.assertGreater(u1_after.points, 0)
        self.assertGreater(u1_after.exp, 0)
        self.assertGreater(u2_after.points, 0)
        self.assertGreater(u2_after.exp, 0)
        session.close()

if __name__ == "__main__":
    unittest.main()
