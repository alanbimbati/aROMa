import unittest
from database import Database
from models.user import Utente
from models.pve import Mob
from models.dungeon import Dungeon, DungeonParticipant
from models.resources import UserResource
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
        
        from models.combat import CombatParticipation
        
        # Create test users
        session = self.db.get_session()
        
        # Clean up in correct order
        session.query(CombatParticipation).delete()
        session.query(Mob).filter_by(chat_id=130001).delete()
        session.query(DungeonParticipant).delete()
        session.query(Dungeon).filter_by(chat_id=130001).delete()
        session.query(UserResource).filter(UserResource.user_id.in_([13001, 13002, 13003])).delete()
        session.query(Utente).filter(Utente.id_telegram.in_([13001, 13002, 13003])).delete()
        session.commit()
        
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

        u1 = get_or_create(13001, "user13_1", "User 13-1", 100)
        u2 = get_or_create(13002, "user13_2", "User 13-2", 0)
        u3 = get_or_create(13003, "user13_3", "User 13-3", 100)
            
        session.commit()
        session.close()
        
        # Clear recent users to avoid pollution from other tests
        UserService._recent_activities.clear()
        
        # Track activity
        self.user_service.track_activity(13001, chat_id=130001)
        self.user_service.track_activity(13002, chat_id=130001)
        self.user_service.track_activity(13003, chat_id=130001)

    def tearDown(self):
        from models.combat import CombatParticipation
        session = self.db.get_session()
        # Clean up in correct order
        session.query(CombatParticipation).delete()
        session.query(Mob).filter_by(chat_id=130001).delete()
        session.query(DungeonParticipant).delete()
        session.query(Dungeon).filter_by(chat_id=130001).delete()
        session.query(UserResource).filter(UserResource.user_id.in_([13001, 13002, 13003])).delete()
        session.query(Utente).filter(Utente.id_telegram.in_([13001, 13002, 13003])).delete()
        session.commit()
        session.close()

    def test_targeting_avoids_dead_users(self):
        """Verify that mobs don't attack dead users"""
        success, msg, mob_id = self.pve_service.spawn_specific_mob(chat_id=130001)
        self.assertTrue(success)
        
        events = self.pve_service.mob_random_attack(specific_mob_id=mob_id, chat_id=130001)
        self.assertIsNotNone(events)
        
        for event in events:
            msg = event['message']
            self.assertNotIn("user2", msg)
            self.assertTrue("user1" in msg or "user3" in msg)

    def test_dungeon_targeting_restriction(self):
        """Verify that dungeon mobs only attack participants"""
        d_id, msg = self.dungeon_service.create_dungeon(130001, 1, 13001)
        self.dungeon_service.join_dungeon(130001, 13001)
        self.dungeon_service.start_dungeon(130001)
        
        session = self.db.get_session()
        mob = session.query(Mob).filter_by(chat_id=130001, is_dead=False).first()
        mob_id = mob.id
        session.close()
        
        events = self.pve_service.mob_random_attack(specific_mob_id=mob_id, chat_id=130001)
        self.assertIsNotNone(events)
        
        for event in events:
            msg = event['message']
            self.assertIn("user1", msg)
            self.assertNotIn("user3", msg)
            self.assertNotIn("user2", msg)

    def test_dungeon_advancement(self):
        """Verify that killing a dungeon mob advances the dungeon"""
        d_id, msg = self.dungeon_service.create_dungeon(130001, 1, 13001)
        self.dungeon_service.join_dungeon(130001, 13001)
        self.dungeon_service.start_dungeon(130001)
        
        # Check stage 1
        session = self.db.get_session()
        all_dungeons = session.query(Dungeon).all()
        print(f"DEBUG: d_id={d_id}, All Dungeons in DB: {[d.id for d in all_dungeons]}")
        dungeon = session.query(Dungeon).filter_by(id=d_id).first()
        self.assertIsNotNone(dungeon, f"Dungeon with id {d_id} not found. All: {[d.id for d in all_dungeons]}")
        self.assertEqual(dungeon.current_stage, 1)
        
        # Kill stage 1 mobs (there are 3)
        for _ in range(3):
            mob = session.query(Mob).filter_by(dungeon_id=d_id, is_dead=False).first()
            if not mob: break # Added this line to ensure the loop doesn't break if mob is None
            mob_id = mob.id
            
            # Re-fetch user and reset cooldown before each attack
            u_temp = session.query(Utente).filter_by(id_telegram=13001).first()
            u_temp.last_attack_time = datetime.datetime.now() - datetime.timedelta(minutes=5)
            session.commit()
            
            # Pass ID instead of object to avoid DetachedInstanceError
            user_id = u_temp.id_telegram
            session.close() 
            
            # Re-fetch user inside attack_mob or pass ID if service supports it
            # Let's use user_service to get a fresh one
            u_fresh = self.user_service.get_user(user_id)
            success, msg, extra = self.pve_service.attack_mob(u_fresh, base_damage=9999, mob_id=mob_id)
            print(f"DEBUG: Attack Mob {mob_id} result: success={success}, msg={msg}")
            self.assertTrue(success, f"Attack failed for mob {mob_id}: {msg}")
            session = self.db.get_session() # Re-open session for the next iteration or checks
        
        print(f"DEBUG: Stage 1 Kill Msg: {msg}")
        
        # Check stage 2
        session = self.db.get_session()
        dungeon = session.query(Dungeon).filter_by(id=d_id).first()
        self.assertEqual(dungeon.current_stage, 2)
        
        # Kill boss
        boss = session.query(Mob).filter_by(dungeon_id=d_id, is_dead=False).first()
        self.assertIsNotNone(boss, "Boss not spawned!")
        boss_id = boss.id
        session.close() # CLOSE BEFORE CALLING SERVICE
        
        # Re-fetch user for the boss fight
        u_temp = session.query(Utente).filter_by(id_telegram=13001).first()
        u_temp.last_attack_time = datetime.datetime.now() - datetime.timedelta(minutes=5)
        session.commit()
        
        success, msg, extra = self.pve_service.attack_mob(u_temp, base_damage=99999, mob_id=boss_id)
        print(f"DEBUG: Boss Kill Msg: {msg}")
        self.assertTrue(success)
        
        # Check completed
        session = self.db.get_session()
        dungeon = session.query(Dungeon).filter_by(id=d_id).first()
        self.assertEqual(dungeon.status, "completed")
        session.close()

    def test_dungeon_mob_targeting(self):
        """Test that dungeon mobs can find and attack participants"""
        # Create dungeon and participant
        d_id, msg = self.dungeon_service.create_dungeon(130001, 1, 13001)
        self.dungeon_service.join_dungeon(130001, 13001)
        
        # Start dungeon (spawns mobs)
        success, msg, events = self.dungeon_service.start_dungeon(130001)
        self.assertTrue(success)
        
        # Get spawned mob
        session = self.db.get_session()
        mob = session.query(Mob).filter_by(dungeon_id=d_id).first()
        self.assertIsNotNone(mob)
        mob_id = mob.id
        session.close()
        
        # Trigger attack
        # Force track activity to ensure user is "recent" if that's required
        self.user_service.track_activity(13001, 130001)
        
        events = self.pve_service.mob_random_attack(specific_mob_id=mob_id, chat_id=130001)
        
        # If events is empty or None, it failed to find target
        print(f"Attack Events: {events}")
        self.assertIsNotNone(events)
        self.assertTrue(len(events) > 0, "Mob failed to attack dungeon participant")
        
        # Verify damage
        attacked_user_id = None
        for event in events:
            msg = event['message']
            if "@user13_1" in msg or "User 13-1" in msg: attacked_user_id = 13001
            elif "@user13_3" in msg or "User 13-3" in msg: attacked_user_id = 13003
        
        self.assertIsNotNone(attacked_user_id, f"Could not identify attacked user in events: {events}")
        
        session = self.db.get_session()
        user = session.query(Utente).filter_by(id_telegram=attacked_user_id).first()
        self.assertLess(user.current_hp, user.max_health)
        session.close()

    def test_dungeon_participants_persistence(self):
        """Test that participants are correctly saved and retrieved"""
        # Create dungeon
        d_id, msg = self.dungeon_service.create_dungeon(130001, 1, 13001)
        self.assertIsNotNone(d_id)
        
        # Verify creator is participant
        parts = self.dungeon_service.get_dungeon_participants(d_id)
        self.assertEqual(len(parts), 1)
        self.assertEqual(parts[0].user_id, 13001)
        
        # Join another user
        success, msg = self.dungeon_service.join_dungeon(130001, 13002)
        self.assertTrue(success)
        
        # Verify both are participants
        parts = self.dungeon_service.get_dungeon_participants(d_id)
        self.assertEqual(len(parts), 2)
        user_ids = [p.user_id for p in parts]
        self.assertIn(13001, user_ids)
        self.assertIn(13002, user_ids)
        
        # Start dungeon
        success, msg, events = self.dungeon_service.start_dungeon(130001)
        self.assertTrue(success)
        
        # Verify participants still exist after start
        parts = self.dungeon_service.get_dungeon_participants(d_id)
        self.assertEqual(len(parts), 2)
        
        # Verify active dungeon retrieval
        dungeon = self.dungeon_service.get_user_active_dungeon(13001)
        self.assertIsNotNone(dungeon)
        self.assertEqual(dungeon.id, d_id)
        
        dungeon = self.dungeon_service.get_user_active_dungeon(13002)
        self.assertIsNotNone(dungeon)
        self.assertEqual(dungeon.id, d_id)

    def test_flee_dungeon_ghost(self):
        """Test fleeing from a dungeon mob when NOT a participant"""
        # Create dungeon
        d_id, msg = self.dungeon_service.create_dungeon(130001, 1, 13001)
        self.dungeon_service.start_dungeon(130001)
        
        # Get mob
        session = self.db.get_session()
        mob = session.query(Mob).filter_by(dungeon_id=d_id).first()
        mob_id = mob.id
        session.close()
        
        # User 13002 is NOT a participant
        # But let's say they get attacked via fallback (simulated by just calling flee)
        user_ghost = self.user_service.get_user(13002)
        
        # Try to flee
        success, msg = self.pve_service.flee_mob(user_ghost, mob_id)
        
        print(f"Ghost Flee Result: {success}, {msg}")
        
        # Should NOT return "Non sei un partecipante"
        # Should return standard flee message (Success or Blocked)
        self.assertNotIn("Non sei un partecipante", msg)
        self.assertTrue("fuggito" in msg or "bloccato" in msg)

if __name__ == "__main__":
    unittest.main()
