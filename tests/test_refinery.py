#!/usr/bin/env python3
import sys
import os
import unittest
from datetime import datetime, timedelta
from sqlalchemy import text

# Add project root to path
sys.path.append(os.getcwd())

from database import Database
from services.crafting_service import CraftingService
from services.user_service import UserService
from services.guild_service import GuildService
from models.user import Utente

class TestRefinery(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.db = Database()
        cls.crafting = CraftingService()
        cls.user_service = UserService()
        cls.guild_service = GuildService()
        
        # Test IDs
        cls.test_user_id = 1234567890
        cls.test_guild_id = 998877
        
        # Setup Test Environment
        session = cls.db.get_session()
        try:
            # Cleanup
            session.execute(text("DELETE FROM refinery_queue WHERE user_id = :uid"), {"uid": cls.test_user_id})
            session.execute(text("DELETE FROM user_refined_materials WHERE user_id = :uid"), {"uid": cls.test_user_id})
            session.execute(text("DELETE FROM user_resources WHERE user_id = :uid"), {"uid": cls.test_user_id})
            session.execute(text("DELETE FROM guilds WHERE id = :gid"), {"gid": cls.test_guild_id})
            session.execute(text("DELETE FROM utente WHERE \"id_Telegram\" = :uid"), {"uid": cls.test_user_id})
            
            # Create User
            user = Utente(
                id_telegram=cls.test_user_id,
                nome="RefineryTester",
                username="refinery_tester",
                livello=50
            )
            session.add(user)
            session.flush() # Ensure user exists for FK
            
            # Create Guild
            session.execute(text("""
                INSERT INTO guilds (id, name, leader_id, armory_level)
                VALUES (:gid, 'Refinery Guild', :uid, 5)
            """), {"gid": cls.test_guild_id, "uid": cls.test_user_id})
            
            session.commit()
        finally:
            session.close()

    def test_01_formula_consistency(self):
        """Test the material generation formula logic in complete_refinement"""
        print("\n🧪 Test: Formula Consistency")
        # Formula outputs: (rottami, pregiato, diamante)
        # We'll use a mockable test if possible, but we can just check the results of complete_refinement
        # First, add a job
        daily = self.crafting.get_daily_refinable_resource()
        self.assertIsNotNone(daily, "Should have a daily refinable resource")
        
        session = self.db.get_session()
        # Add resources
        session.execute(text("INSERT INTO user_resources (user_id, resource_id, quantity) VALUES (:uid, :rid, 100)"), 
                       {"uid": self.test_user_id, "rid": daily['id']})
        session.commit()
        session.close()
        
        # Start
        start_res = self.crafting.start_refinement(self.test_guild_id, self.test_user_id, daily['id'], 100)
        self.assertTrue(start_res['success'])
        
        # Complete
        session = self.db.get_session()
        job = session.execute(text("SELECT id FROM refinery_queue WHERE user_id = :uid AND status = 'in_progress'"), {"uid": self.test_user_id}).fetchone()
        self.assertIsNotNone(job)
        
        # Process completion
        res = self.crafting.complete_refinement(job[0], char_level=50, prof_level=1, armory_level=5)
        self.assertTrue(res['success'])
        
        print(f"✅ Gained: {res['materials']}")
        self.assertIn('Rottami', res['materials'])
        self.assertIn('Materiale Pregiato', res['materials'])
        self.assertIn('Diamante', res['materials'])
        
        total = sum(res['materials'].values())
        self.assertGreater(total, 0)
        session.close()

    def test_02_daily_lock(self):
        """Test that only today's resource can be refined"""
        print("\n🧪 Test: Daily Resource Lock")
        session = self.db.get_session()
        # Get a resource that is NOT today's daily
        daily = self.crafting.get_daily_refinable_resource()
        other = session.execute(text("SELECT id FROM resources WHERE id != :id LIMIT 1"), {"id": daily['id']}).fetchone()
        
        if other:
            res = self.crafting.start_refinement(self.test_guild_id, self.test_user_id, other[0], 10)
            self.assertFalse(res['success'])
            self.assertEqual(res['error'], "Questo materiale non può essere raffinato oggi!")
            print("✅ Correctly blocked refinement of non-daily resource")
        session.close()

    def test_03_queue_processing(self):
        """Test process_refinery_queue automatically completes jobs"""
        print("\n🧪 Test: Queue Automatic Processing")
        daily = self.crafting.get_daily_refinable_resource()
        
        # Add resource to start
        session = self.db.get_session()
        session.execute(text("UPDATE user_resources SET quantity = 100 WHERE user_id = :uid AND resource_id = :rid"), 
                       {"uid": self.test_user_id, "rid": daily['id']})
        session.commit()
        session.close()
        
        # Start
        self.crafting.start_refinement(self.test_guild_id, self.test_user_id, daily['id'], 20)
        
        # Force completion time to past
        session = self.db.get_session()
        session.execute(text("UPDATE refinery_queue SET completion_time = :now WHERE user_id = :uid AND status = 'in_progress'"), 
                       {"now": datetime.now() - timedelta(seconds=10), "uid": self.test_user_id})
        session.commit()
        session.close()
        
        # Process
        results = self.crafting.process_refinery_queue()
        # Filter for our test user
        user_results = [r for r in results if r.get('user_id') == self.test_user_id]
        self.assertTrue(len(user_results) > 0)
        print(f"✅ Auto-processed {len(user_results)} jobs for user")
        
    def test_04_inventory_tracking(self):
        """Verify user_refined_materials table reflects gains"""
        print("\n🧪 Test: Inventory Tracking")
        session = self.db.get_session()
        mats = session.execute(text("SELECT material_id, quantity FROM user_refined_materials WHERE user_id = :uid"), 
                              {"uid": self.test_user_id}).fetchall()
        
        self.assertGreater(len(mats), 0)
        for mid, qty in mats:
            self.assertGreater(qty, 0)
            print(f"✅ Material ID {mid} has quantity {qty}")
        session.close()

if __name__ == '__main__':
    unittest.main()
