import unittest
from services.pve_service import PvEService
from services.user_service import UserService
from models.pve import Mob, Raid
from database import Database

class TestPvE(unittest.TestCase):
    def setUp(self):
        self.db = Database()
        self.pve_service = PvEService()
        self.user_service = UserService()
        
        # Test user
        self.test_id = 123456789
        self.user_service.create_user(self.test_id, "testuser", "Test", "User")
        self.user = self.user_service.get_user(self.test_id)
        self.user_service.update_user(self.test_id, {'luck_boost': 0})

    def test_daily_mob(self):
        # Clear existing mobs
        session = self.db.get_session()
        session.query(Mob).delete()
        session.commit()
        session.close()
        
        # Spawn
        self.pve_service.spawn_daily_mob()
        
        # Get mob ID
        session = self.db.get_session()
        mob = session.query(Mob).filter_by(is_dead=False).first()
        self.assertIsNotNone(mob)
        mob_id = mob.id
        print(f"Spawned mob ID: {mob_id}")
        session.close()
        
        # Attack
        success, msg = self.pve_service.attack_mob(self.user, 1000) # Kill it
        self.assertTrue(success)
        print(f"Attack result: {msg}")
        
        # Verify dead
        session = self.db.get_session()
        mob = session.query(Mob).filter_by(id=mob_id).first()
        self.assertTrue(mob.is_dead)
        session.close()

    def test_raid(self):
        # Clear existing raids
        session = self.db.get_session()
        session.query(Raid).delete()
        session.commit()
        session.close()
        
        # Spawn
        self.pve_service.spawn_raid_boss()
        
        # Get raid ID
        session = self.db.get_session()
        raid = session.query(Raid).filter_by(is_active=True).first()
        self.assertIsNotNone(raid)
        raid_id = raid.id
        print(f"Spawned raid ID: {raid_id}")
        session.close()
        
        # Attack
        success, msg = self.pve_service.attack_raid_boss(self.user, 100)
        self.assertTrue(success)
        print(f"Raid attack result: {msg}")
        
        # Kill
        success, msg = self.pve_service.attack_raid_boss(self.user, 100000)
        self.assertTrue(success)
        print(f"Raid kill result: {msg}")
        
        # Verify inactive
        session = self.db.get_session()
        raid = session.query(Raid).filter_by(id=raid_id).first()
        self.assertFalse(raid.is_active)
        session.close()

if __name__ == '__main__':
    unittest.main()
