#!/usr/bin/env python3
"""
Unit tests for Crafting System
Tests:
- Resource drops from mobs
- Resource inventory management
- Recipe-based crafting with resource consumption
- Crafting queue and completion
- Guild armory level effects on quality
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import unittest
from database import Database
from sqlalchemy import text
from services.crafting_service import CraftingService
from datetime import datetime, timedelta
import json
import time

class TestCraftingSystem(unittest.TestCase):
    """Test crafting mechanics and resource management"""
    
    @classmethod
    def setUpClass(cls):
        """Set up test database"""
        cls.db = Database()
        cls.crafting = CraftingService()
        
        # Test data
        cls.test_user_id = 999777666
        cls.test_guild_id = 888777666
        
        session = cls.db.get_session()
        try:
             # Force cleanup of resources to ensure clean init
             session.execute(text('TRUNCATE TABLE resources RESTART IDENTITY CASCADE'))
             session.commit()
        except Exception:
             session.rollback()
        finally:
             session.close()

        # Initialize crafting system
        print("\n🔧 Initializing crafting system...")
        os.system('python3 init_crafting_db.py > /dev/null 2>&1')
        
        session = cls.db.get_session()
        try:
            # Clean up test data
            session.execute(text('DELETE FROM crafting_queue WHERE user_id = :uid'), 
                          {"uid": cls.test_user_id})
            session.execute(text('DELETE FROM user_resources WHERE user_id = :uid'),
                          {"uid": cls.test_user_id})
            session.execute(text('DELETE FROM user_equipment WHERE user_id = :uid'),
                          {"uid": cls.test_user_id})
            session.execute(text('DELETE FROM guild_buildings WHERE guild_id = :gid'),
                          {"gid": cls.test_guild_id})
            session.execute(text('DELETE FROM guilds WHERE id = :gid'),
                          {"gid": cls.test_guild_id})
            session.execute(text('DELETE FROM utente WHERE "id_Telegram" = :uid'),
                          {"uid": cls.test_user_id})
            session.commit()
            
            # Create test user
            session.execute(text("""
                INSERT INTO utente ("id_Telegram", username, nome, livello)
                VALUES (:uid, 'CraftTestUser', 'CraftTestUser', 50)
            """), {"uid": cls.test_user_id})
            
            # Create test guild armory
            session.execute(text("""
                INSERT INTO guild_buildings (guild_id, building_type, level)
                VALUES (:gid, 'armory', 3)
            """), {"gid": cls.test_guild_id})
            
            # Create guild in guilds table (CraftingService uses this)
            session.execute(text("""
                INSERT INTO guilds (id, name, leader_id, armory_level)
                VALUES (:gid, 'TestGuild', :uid, 3)
            """), {"gid": cls.test_guild_id, "uid": cls.test_user_id})
            
            # Ensure essential equipment for crafting tests exists
            # test_04/05 use ID 1, test_06 uses ID 8
            for eid, name, req in [(1, 'Gi della Tartaruga', '{"Rottami": 5}'), 
                                 (8, 'Guanti Vegeta', '{"Pelle Logora": 5}')]:
                exists = session.execute(text("SELECT id FROM equipment WHERE id = :id"), {"id": eid}).scalar()
                if not exists:
                    session.execute(text("""
                        INSERT INTO equipment (id, name, slot, rarity, min_level, crafting_time, crafting_requirements)
                        VALUES (:id, :name, 'chest', 1, 1, 10, :req)
                    """), {"id": eid, "name": name, "req": req})
            
            session.commit()
            
        finally:
            session.close()
    
    def setUp(self):
        """Clean resources and crafting before each test"""
        session = self.db.get_session()
        try:
            session.execute(text('DELETE FROM crafting_queue WHERE user_id = :uid'),
                          {"uid": self.test_user_id})
            session.execute(text('DELETE FROM user_resources WHERE user_id = :uid'),
                          {"uid": self.test_user_id})
            session.execute(text('DELETE FROM user_equipment WHERE user_id = :uid'),
                          {"uid": self.test_user_id})
            session.commit()
        finally:
            session.close()
    
    def test_01_resource_drop_from_mob(self):
        """Test that killing a mob can drop resources"""
        print("\n🧪 Test 1: Resource drop from mob")
        
        # Simulate killing a level 20 mob
        mob_level = 20
        # Returns tuple (id, image_path) or (None, None)
        result = self.crafting.roll_resource_drop(mob_level, mob_is_boss=False)
        
        if result and result[0]:
            resource_id, _ = result
            # Add resource to user
            success = self.crafting.add_resource_drop(self.test_user_id, resource_id, quantity=1, source="mob")
            self.assertTrue(success, "Resource drop should be added")
            
            # Verify it's in inventory
            resources = self.crafting.get_user_resources(self.test_user_id)
            owned_resources = [r for r in resources if r['quantity'] > 0]
            self.assertEqual(len(owned_resources), 1, "Should have 1 resource type with quantity > 0")
            self.assertEqual(owned_resources[0]['quantity'], 1, "Should have quantity 1")
            print(f"✅ Dropped: {resources[0]['name']} (Rarity {resources[0]['rarity']})")
        else:
            print("✅ No drop this time (20% chance is working)")
    
    def test_02_boss_always_drops_resources(self):
        """Test that bosses always drop resources"""
        print("\n🧪 Test 2: Boss resource drops (100% rate)")
        
        # Simulate killing a boss
        result = self.crafting.roll_resource_drop(50, mob_is_boss=True)
        
        self.assertIsNotNone(result, "Boss should always drop a resource (tuple)")
        resource_id, _ = result
        self.assertIsNotNone(resource_id, "Boss should drop a VALID resource (not None)")
        
        success = self.crafting.add_resource_drop(self.test_user_id, resource_id, quantity=3, source="boss")
        self.assertTrue(success, "Boss resource drop should be added")
        
        resources = self.crafting.get_user_resources(self.test_user_id)
        # Filter for non-zero quantity
        owned_resources = [r for r in resources if r['quantity'] > 0]
        self.assertEqual(len(owned_resources), 1, "Should have 1 owned resource type")
        self.assertGreaterEqual(owned_resources[0]['quantity'], 3, "Should have at least 3 from boss")
        print(f"✅ Boss dropped: {owned_resources[0]['name']} x{owned_resources[0]['quantity']}")
    
    def test_03_resource_stacking(self):
        """Test that duplicate resources stack"""
        print("\n🧪 Test 3: Resource stacking")
        
        session = self.db.get_session()
        try:
            # Get Rottami ID
            iron_id = session.execute(text("SELECT id FROM resources WHERE name = 'Rottami'")).scalar()
            
            # Add 5 Rottami
            self.crafting.add_resource_drop(self.test_user_id, iron_id, quantity=5)
            
            # Add 3 more Rottami
            self.crafting.add_resource_drop(self.test_user_id, iron_id, quantity=3)
            
            # Should have 8 total
            resources = self.crafting.get_user_resources(self.test_user_id)
            # Filter for non-zero quantity
            owned_resources = [r for r in resources if r['quantity'] > 0]
            self.assertEqual(len(owned_resources), 1, "Should only have 1 resource type")
            self.assertEqual(owned_resources[0]['quantity'], 8, "Should have 8 Rottami stacked")
            print(f"✅ Stacked correctly: {owned_resources[0]['name']} x{owned_resources[0]['quantity']}")
            
        finally:
            session.close()
    
    def test_04_craft_without_resources(self):
        """Test that crafting fails without resources"""
        print("\n🧪 Test 4: Crafting without resources (should fail)")
        
        session = self.db.get_session()
        try:
            # Try to craft Gi della Tartaruga (equipment ID 1) without resources
            equipment_id = 1
            
            result = self.crafting.start_crafting(self.test_guild_id, self.test_user_id, equipment_id)
            
            self.assertFalse(result['success'], "Crafting should fail without resources")
            self.assertIn('error', result, "Should have error message")
            print(f"✅ Correctly blocked: {result['error']}")
            
        finally:
            session.close()
    
    def test_05_craft_with_resources(self):
        """Test successful crafting with resources"""
        print("\n🧪 Test 5: Successful crafting with resources")
        
        session = self.db.get_session()
        try:
            # Ensure equipment 1 exists (it might have been deleted by other tests)
            exists = session.execute(text("SELECT id FROM equipment WHERE id = 1")).scalar()
            if not exists:
                session.execute(text("""
                    INSERT INTO equipment (id, name, slot, rarity, min_level, crafting_time, crafting_requirements)
                    VALUES (1, 'Gi della Tartaruga', 'chest', 1, 1, 10, '{"Rottami": 5}')
                """))
                session.commit()

            # Get crafting info for Gi della Tartaruga (ID 1)
            equipment = session.execute(text("""
                SELECT id, crafting_requirements FROM equipment WHERE id = 1
            """)).fetchone()
            
            equipment_id, crafting_requirements = equipment
            resources_needed = json.loads(crafting_requirements)
            
            # Add required resources
            for resource_name, quantity in resources_needed.items():
                resource_id = session.execute(text("""
                    SELECT id FROM resources WHERE name = :name
                """), {"name": resource_name}).scalar()
                self.crafting.add_resource_drop(self.test_user_id, resource_id, quantity=quantity)
            
            # Verify resources before crafting
            resources_before = self.crafting.get_user_resources(self.test_user_id)
            print(f"📦 Resources before: {len(resources_before)} types")
            
            # Start crafting
            result = self.crafting.start_crafting(self.test_guild_id, self.test_user_id, equipment_id)
            
            self.assertTrue(result['success'], "Crafting should succeed")
            self.assertIn('completion_time', result, "Should have completion time")
            
            # Verify resources were consumed
            resources_after = self.crafting.get_user_resources(self.test_user_id)
            print(f"📦 Resources after: {len(resources_after)} types (consumed)")
            
            # Should have no resources left (all consumed)
            total_after = sum(r['quantity'] for r in resources_after)
            self.assertEqual(total_after, 0, "All resources should be consumed")
            
            print(f"✅ Crafting started! Completes in {result['crafting_time']}s")
            
        finally:
            session.close()
    
    def test_06_complete_crafting(self):
        """Test completing a crafting job"""
        print("\n🧪 Test 6: Completing crafting job")
        
        session = self.db.get_session()
        try:
            # Get crafting info for Guanti Vegeta (ID 8)
            equipment = session.execute(text("""
                SELECT id, crafting_requirements FROM equipment WHERE id = 8
            """)).fetchone()
            
            equipment_id, crafting_requirements = equipment
            resources_needed = json.loads(crafting_requirements)
            
            # Add resources and start crafting
            for resource_name, quantity in resources_needed.items():
                resource_id = session.execute(text("""
                    SELECT id FROM resources WHERE name = :name
                """), {"name": resource_name}).scalar()
                self.crafting.add_resource_drop(self.test_user_id, resource_id, quantity=quantity)
            
            craft_result = self.crafting.start_crafting(self.test_guild_id, self.test_user_id, equipment_id)
            if not craft_result['success']:
                print(f"❌ Crafting failed: {craft_result.get('error')}")
            self.assertTrue(craft_result['success'], "Crafting should start")
            
            # Get crafting queue ID
            queue_id = session.execute(text("""
                SELECT id FROM crafting_queue 
                WHERE user_id = :uid AND status = 'in_progress'
                ORDER BY id DESC LIMIT 1
            """), {"uid": self.test_user_id}).scalar()
            
            # Fast-forward completion time (for testing)
            session.execute(text("""
                UPDATE crafting_queue
                SET completion_time = :time
                WHERE id = :id
            """), {"id": queue_id, "time": datetime.now() - timedelta(seconds=1)})
            session.commit()
            
            # Complete crafting
            armory_level = self.crafting.get_guild_armory_level(self.test_guild_id)
            complete_result = self.crafting.complete_crafting(queue_id, armory_level=armory_level, profession_level=1)
            
            self.assertTrue(complete_result['success'], "Crafting should complete")
            self.assertEqual(complete_result['equipment_id'], equipment_id, "Should craft correct item")
            
            # Verify item was added to inventory
            item_count = session.execute(text("""
                SELECT COUNT(*) FROM user_equipment
                WHERE user_id = :uid AND equipment_id = :eid
            """), {"uid": self.test_user_id, "eid": equipment_id}).scalar()
            
            self.assertGreaterEqual(item_count, 1, "Item should be in inventory")
            
            rarity_text = ["", "Common", "Uncommon", "Rare", "Epic", "Legendary"][complete_result['final_rarity']]
            upgrade_text = " (UPGRADED!)" if complete_result['upgraded'] else ""
            print(f"✅ Crafted: Equipment #{equipment_id} - {rarity_text}{upgrade_text}")
            
        finally:
            session.close()
    
    # Removed obsolete test_07 (recipes table does not exist)
    
    @classmethod
    def tearDownClass(cls):
        """Clean up test data"""
        session = cls.db.get_session()
        try:
            session.execute(text('DELETE FROM crafting_queue WHERE user_id = :uid'),
                          {"uid": cls.test_user_id})
            session.execute(text('DELETE FROM user_resources WHERE user_id = :uid'),
                          {"uid": cls.test_user_id})
            session.execute(text('DELETE FROM user_equipment WHERE user_id = :uid'),
                          {"uid": cls.test_user_id})
            session.execute(text('DELETE FROM guild_buildings WHERE guild_id = :gid'),
                          {"gid": cls.test_guild_id})
            session.execute(text('DELETE FROM guilds WHERE id = :gid'),
                          {"gid": cls.test_guild_id})
            session.execute(text('DELETE FROM utente WHERE "id_Telegram" = :uid'),
                          {"uid": cls.test_user_id})
            session.commit()
            print("\n🧹 Test cleanup complete")
        finally:
            session.close()

if __name__ == '__main__':
    print("\n" + "="*60)
    print("🧪 CRAFTING SYSTEM UNIT TESTS")
    print("="*60)
    
    # Run tests
    suite = unittest.TestLoader().loadTestsFromTestCase(TestCraftingSystem)
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # Summary
    print("\n" + "="*60)
    print("📊 TEST SUMMARY")
    print("="*60)
    print(f"✅ Tests run: {result.testsRun}")
    print(f"❌ Failures: {len(result.failures)}")
    print(f"⚠️  Errors: {len(result.errors)}")
    print(f"⏭️  Skipped: {len(result.skipped)}")
    
    if result.wasSuccessful():
        print("\n🎉 ALL CRAFTING TESTS PASSED!")
    else:
        print("\n❌ SOME TESTS FAILED")
    
    sys.exit(0 if result.wasSuccessful() else 1)
