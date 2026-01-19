import unittest
from database import Database
from models.user import Utente
from models.pve import Mob
from models.dungeon import Dungeon, DungeonParticipant
from services.user_service import UserService
from services.pve_service import PvEService
from services.dungeon_service import DungeonService
import datetime
import time

class TestDungeonLogic(unittest.TestCase):
    def setUp(self):
        self.db = Database()
        self.user_service = UserService()
        self.pve_service = PvEService()
        self.dungeon_service = DungeonService()
        
        # Create test users
        session = self.db.get_session()
        
        def get_or_create(uid, username, nome, vita_val):
            u = session.query(Utente).filter_by(id_telegram=uid).first()
            if not u:
                u = Utente(id_telegram=uid, username=username, nome=nome)
                session.add(u)
            u.username = username
            u.nome = nome
            u.vita = vita_val
            u.health = vita_val if vita_val > 0 else 0
            u.current_hp = vita_val if vita_val > 0 else 0
            u.max_health = 100
            u.last_attack_time = datetime.datetime.now() - datetime.timedelta(hours=1)
            if hasattr(u, 'fatigue'): u.fatigue = 0
            return u

        u1 = get_or_create(12345, "user1", "User 1", 100)
        u2 = get_or_create(67890, "user2", "User 2", 0)
        u3 = get_or_create(11111, "user3", "User 3", 100)
            
        session.commit()
        session.close()
        
        # Clear recent users to avoid pollution from other tests
        UserService._recent_users.clear()
        
        # Track activity
        self.user_service.track_activity(12345, chat_id=999)
        self.user_service.track_activity(67890, chat_id=999)
        self.user_service.track_activity(11111, chat_id=999)

    def tearDown(self):
        session = self.db.get_session()
        session.query(Mob).filter_by(chat_id=999).delete()
        session.query(DungeonParticipant).delete()
        session.query(Dungeon).filter_by(chat_id=999).delete()
        session.query(Utente).filter(Utente.id_telegram.in_([12345, 67890, 11111])).delete()
        session.commit()
        session.close()

    def test_targeting_avoids_dead_users(self):
        """Verify that mobs don't attack dead users"""
        success, msg, mob_id = self.pve_service.spawn_specific_mob(chat_id=999)
        self.assertTrue(success)
        
        events = self.pve_service.mob_random_attack(specific_mob_id=mob_id, chat_id=999)
        self.assertIsNotNone(events)
        
        for event in events:
            msg = event['message']
            self.assertNotIn("user2", msg)
            self.assertTrue("user1" in msg or "user3" in msg)

    def test_dungeon_targeting_restriction(self):
        """Verify that dungeon mobs only attack participants"""
        d_id, msg = self.dungeon_service.create_dungeon(999, "Test Dungeon")
        self.dungeon_service.join_dungeon(999, 12345)
        self.dungeon_service.start_dungeon(999)
        
        session = self.db.get_session()
        mob = session.query(Mob).filter_by(chat_id=999, is_dead=False).first()
        mob_id = mob.id
        session.close()
        
        events = self.pve_service.mob_random_attack(specific_mob_id=mob_id, chat_id=999)
        self.assertIsNotNone(events)
        
        for event in events:
            msg = event['message']
            self.assertIn("user1", msg)
            self.assertNotIn("user3", msg)
            self.assertNotIn("user2", msg)

    def test_dungeon_advancement(self):
        """Verify that killing a dungeon mob advances the dungeon"""
        d_id, msg = self.dungeon_service.create_dungeon(999, "Test Dungeon", total_stages=2)
        self.dungeon_service.join_dungeon(999, 12345)
        self.dungeon_service.start_dungeon(999)
        
        # Check stage 1
        session = self.db.get_session()
        all_dungeons = session.query(Dungeon).all()
        print(f"DEBUG: d_id={d_id}, All Dungeons in DB: {[d.id for d in all_dungeons]}")
        dungeon = session.query(Dungeon).filter_by(id=d_id).first()
        self.assertIsNotNone(dungeon, f"Dungeon with id {d_id} not found. All: {[d.id for d in all_dungeons]}")
        self.assertEqual(dungeon.current_stage, 1)
        
        # Kill stage 1 mob
        mob = session.query(Mob).filter_by(dungeon_id=d_id, is_dead=False).first()
        mob_id = mob.id
        user1 = session.query(Utente).filter_by(id_telegram=12345).first()
        session.close() # CLOSE BEFORE CALLING SERVICE
        
        success, msg = self.pve_service.attack_mob(user1, base_damage=9999, mob_id=mob_id)
        print(f"DEBUG: Stage 1 Kill Msg: {msg}")
        self.assertTrue(success)
        
        # Check stage 2
        session = self.db.get_session()
        dungeon = session.query(Dungeon).filter_by(id=d_id).first()
        self.assertEqual(dungeon.current_stage, 2)
        
        # Kill boss
        boss = session.query(Mob).filter_by(dungeon_id=d_id, is_dead=False).first()
        self.assertIsNotNone(boss, "Boss not spawned!")
        boss_id = boss.id
        session.close() # CLOSE BEFORE CALLING SERVICE
        
        success, msg = self.pve_service.attack_mob(user1, base_damage=99999, mob_id=boss_id)
        print(f"DEBUG: Boss Kill Msg: {msg}")
        self.assertTrue(success)
        
        # Check completed
        session = self.db.get_session()
        dungeon = session.query(Dungeon).filter_by(id=d_id).first()
        self.assertEqual(dungeon.status, "completed")
        session.close()

if __name__ == "__main__":
    unittest.main()
