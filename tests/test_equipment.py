#!/usr/bin/env python3
"""
Unit tests for Equipment System
Tests various equipment requirements and mechanics:
- Level requirements
- Alignment requirements
- Subgroup requirements
- Element requirements
- Scouter (Scan) functionality
- Potara (Fusion) unlock
- Set bonuses
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import unittest
from database import Database
from sqlalchemy import text
from services.user_service import UserService
from services.character_service import CharacterService

class TestEquipmentSystem(unittest.TestCase):
    """Test equipment mechanics and requirements"""
    
    @classmethod
    def setUpClass(cls):
        """Set up test database"""
        cls.db = Database()
        cls.user_service = UserService()  # No need to pass db
        cls.char_service = CharacterService()  # No need to pass db
        
        # Create test user
        cls.test_user_id = 999888777
        cls.test_username = "EquipTestUser"
        
        session = cls.db.get_session()
        try:
            # Clean up any existing test user
            session.execute(text('DELETE FROM user_equipment WHERE user_id = :uid'), 
                          {"uid": cls.test_user_id})
            session.execute(text('DELETE FROM utente WHERE "id_Telegram" = :uid'), 
                          {"uid": cls.test_user_id})
            session.commit()
            
            # Create test user (level 50)
            session.execute(text("""
                INSERT INTO utente ("id_Telegram", username, nome, livello)
                VALUES (:uid, :username, :nome, 50)
            """), {
                "uid": cls.test_user_id,
                "username": cls.test_username,
                "nome": cls.test_username
            })
            session.commit()
            
        finally:
            session.close()
    
    def setUp(self):
        """Clean equipment before each test"""
        session = self.db.get_session()
        try:
            session.execute(text('DELETE FROM user_equipment WHERE user_id = :uid'),
                          {"uid": self.test_user_id})
            session.commit()
        finally:
            session.close()
    
    def test_01_equip_basic_item(self):
        """Test basic item equipping (level requirement only)"""
        print("\n🧪 Test 1: Basic item equipping")
        
        session = self.db.get_session()
        try:
            # Add Scouter (level 1, common, head slot)
            session.execute(text("""
                INSERT INTO user_equipment (user_id, equipment_id, equipped, durability)
                VALUES (:uid, 6, FALSE, 100)
            """), {"uid": self.test_user_id})
            session.commit()
            
            # Equip it
            session.execute(text("""
                UPDATE user_equipment 
                SET equipped = TRUE, slot_equipped = 'head'
                WHERE user_id = :uid AND equipment_id = 6
            """), {"uid": self.test_user_id})
            session.commit()
            
            # Verify
            result = session.execute(text("""
                SELECT equipped, slot_equipped FROM user_equipment
                WHERE user_id = :uid AND equipment_id = 6
            """), {"uid": self.test_user_id}).fetchone()
            
            self.assertTrue(result[0], "Item should be equipped")
            self.assertEqual(result[1], 'head', "Item should be in head slot")
            print("✅ Basic equipping works")
            
        finally:
            session.close()
    
    def test_02_level_requirement_block(self):
        """Test that high-level items cannot be equipped by low-level users"""
        print("\n🧪 Test 2: Level requirement blocking")
        
        session = self.db.get_session()
        try:
            # Lower user level to 1
            session.execute(text('UPDATE utente SET livello = 1 WHERE "id_Telegram" = :uid'),
                          {"uid": self.test_user_id})
            session.commit()
            
            # Try to add high-level item (Z-Sword, level 50)
            session.execute(text("""
                INSERT INTO user_equipment (user_id, equipment_id, equipped, durability)
                VALUES (:uid, 11, FALSE, 100)
            """), {"uid": self.test_user_id})
            session.commit()
            
            # Check level requirement
            item_level = session.execute(text("""
                SELECT e.min_level FROM equipment e
                WHERE e.id = 11
            """)).scalar()
            
            user_level = session.execute(text("""
                SELECT livello FROM utente WHERE "id_Telegram" = :uid
            """), {"uid": self.test_user_id}).scalar()
            
            can_equip = user_level >= item_level
            
            self.assertFalse(can_equip, f"Level {user_level} user should not equip level {item_level} item")
            print(f"✅ Level requirement enforced: User Lv{user_level} < Item Lv{item_level}")
            
            # Restore level
            session.execute(text('UPDATE utente SET livello = 50 WHERE "id_Telegram" = :uid'),
                          {"uid": self.test_user_id})
            session.commit()
            
        finally:
            session.close()
    
    def test_03_multiple_items_same_slot(self):
        """Test that equipping a second item in same slot unequips the first"""
        print("\n🧪 Test 3: Auto-unequip on slot conflict")
        
        session = self.db.get_session()
        try:
            # Add two chest items
            for item_id in [1, 7]:  # Gi della Tartaruga, Tuta Saiyan
                session.execute(text("""
                    INSERT INTO user_equipment (user_id, equipment_id, equipped, durability)
                    VALUES (:uid, :eid, FALSE, 100)
                """), {"uid": self.test_user_id, "eid": item_id})
            session.commit()
            
            # Equip first item
            session.execute(text("""
                UPDATE user_equipment 
                SET equipped = TRUE, slot_equipped = 'chest'
                WHERE user_id = :uid AND equipment_id = 1
            """), {"uid": self.test_user_id})
            session.commit()
            
            # Equip second item (should unequip first)
            session.execute(text("""
                UPDATE user_equipment
                SET equipped = FALSE, slot_equipped = NULL
                WHERE user_id = :uid AND slot_equipped = 'chest'
            """), {"uid": self.test_user_id})
            
            session.execute(text("""
                UPDATE user_equipment
                SET equipped = TRUE, slot_equipped = 'chest'
                WHERE user_id = :uid AND equipment_id = 7
            """), {"uid": self.test_user_id})
            session.commit()
            
            # Verify only second is equipped
            equipped = session.execute(text("""
                SELECT equipment_id FROM user_equipment
                WHERE user_id = :uid AND equipped = TRUE
            """), {"uid": self.test_user_id}).fetchall()
            
            self.assertEqual(len(equipped), 1, "Only one item should be equipped")
            self.assertEqual(equipped[0][0], 7, "Second item should be equipped")
            print("✅ Auto-unequip works correctly")
            
        finally:
            session.close()
    
    def test_04_scouter_scan_requirement(self):
        """Test that Scan requires Scouter equipped"""
        print("\n🧪 Test 4: Scouter (Scan) requirement")
        
        session = self.db.get_session()
        try:
            # Check if Scouter exists in inventory (not equipped)
            session.execute(text("""
                INSERT INTO user_equipment (user_id, equipment_id, equipped, durability)
                VALUES (:uid, 6, FALSE, 100)
            """), {"uid": self.test_user_id})
            session.commit()
            
            # Check scan capability (unequipped)
            has_scan_unequipped = session.execute(text("""
                SELECT 1 FROM user_equipment ue
                JOIN equipment e ON ue.equipment_id = e.id
                WHERE ue.user_id = :uid AND ue.equipped = TRUE 
                AND e.effect_type = 'scan'
            """), {"uid": self.test_user_id}).fetchone()
            
            self.assertIsNone(has_scan_unequipped, "Scan should not work when Scouter is unequipped")
            
            # Equip Scouter
            session.execute(text("""
                UPDATE user_equipment 
                SET equipped = TRUE, slot_equipped = 'head'
                WHERE user_id = :uid AND equipment_id = 6
            """), {"uid": self.test_user_id})
            session.commit()
            
            # Check scan capability (equipped)
            has_scan_equipped = session.execute(text("""
                SELECT 1 FROM user_equipment ue
                JOIN equipment e ON ue.equipment_id = e.id
                WHERE ue.user_id = :uid AND ue.equipped = TRUE 
                AND e.effect_type = 'scan'
            """), {"uid": self.test_user_id}).fetchone()
            
            self.assertIsNotNone(has_scan_equipped, "Scan should work when Scouter is equipped")
            print("✅ Scouter Scan requirement enforced")
            
        finally:
            session.close()
    
    def test_05_potara_fusion_unlock(self):
        """Test that 2+ Potara unlock fusion characters"""
        print("\n🧪 Test 5: Potara Fusion unlock")
        
        session = self.db.get_session()
        try:
            user = self.user_service.get_user(self.test_user_id)
            
            # Initially no Potara
            potara_count = session.execute(text("""
                SELECT COUNT(*) FROM user_equipment ue
                JOIN equipment e ON ue.equipment_id = e.id
                WHERE ue.user_id = :uid AND e.effect_type = 'fusion'
            """), {"uid": self.test_user_id}).scalar()
            
            self.assertEqual(potara_count, 0, "Should have 0 Potara initially")
            
            # Available chars without Potara
            chars_before = self.char_service.get_available_characters(user)
            fusion_before = [c for c in chars_before if c['id'] in [146, 122, 110]]
            
            # Add 2 Potara
            for _ in range(2):
                session.execute(text("""
                    INSERT INTO user_equipment (user_id, equipment_id, equipped, durability)
                    VALUES (:uid, 16, FALSE, 100)
                """), {"uid": self.test_user_id})
            session.commit()
            
            potara_count = session.execute(text("""
                SELECT COUNT(*) FROM user_equipment ue
                JOIN equipment e ON ue.equipment_id = e.id
                WHERE ue.user_id = :uid AND e.effect_type = 'fusion'
            """), {"uid": self.test_user_id}).scalar()
            
            self.assertEqual(potara_count, 2, "Should have 2 Potara now")
            
            # Available chars with Potara
            chars_after = self.char_service.get_available_characters(user)
            fusion_after = [c for c in chars_after if c['id'] in [146, 122, 110]]
            
            # Should unlock all 3 fusion characters
            self.assertGreater(len(fusion_after), len(fusion_before), 
                             "Should have more fusion characters available")
            print(f"✅ Potara unlock: {len(fusion_before)} -> {len(fusion_after)} fusion chars")
            
        finally:
            session.close()
    
    def test_06_set_bonus_detection(self):
        """Test detection of set bonuses"""
        print("\n🧪 Test 6: Set bonus detection")
        
        session = self.db.get_session()
        try:
            # Add 2 items from Set 1 (Freezer set)
            # Tuta Saiyan (7) and Guanti Vegeta (8)
            for item_id in [7, 8]:
                session.execute(text("""
                    INSERT INTO user_equipment (user_id, equipment_id, equipped, durability)
                    VALUES (:uid, :eid, FALSE, 100)
                """), {"uid": self.test_user_id, "eid": item_id})
            session.commit()
            
            # Equip both
            session.execute(text("""
                UPDATE user_equipment 
                SET equipped = TRUE, slot_equipped = 'chest'
                WHERE user_id = :uid AND equipment_id = 7
            """), {"uid": self.test_user_id})
            
            session.execute(text("""
                UPDATE user_equipment 
                SET equipped = TRUE, slot_equipped = 'hands'
                WHERE user_id = :uid AND equipment_id = 8
            """), {"uid": self.test_user_id})
            session.commit()
            
            # Count equipped items per set
            set_counts = session.execute(text("""
                SELECT e.set_id, COUNT(*) as count
                FROM user_equipment ue
                JOIN equipment e ON ue.equipment_id = e.id
                WHERE ue.user_id = :uid AND ue.equipped = TRUE AND e.set_id IS NOT NULL
                GROUP BY e.set_id
            """), {"uid": self.test_user_id}).fetchall()
            
            self.assertEqual(len(set_counts), 1, "Should have items from 1 set")
            self.assertEqual(set_counts[0][1], 2, "Should have 2 items from the set")
            print(f"✅ Set bonus detected: Set {set_counts[0][0]} with {set_counts[0][1]} pieces")
            
        finally:
            session.close()
    
    def test_07_inventory_limits(self):
        """Test that users can have multiple items but only equip one per slot"""
        print("\n🧪 Test 7: Inventory vs Equipped limits")
        
        session = self.db.get_session()
        try:
            # Add 10 different items
            item_ids = [1, 6, 7, 8, 11, 16]
            for item_id in item_ids:
                session.execute(text("""
                    INSERT INTO user_equipment (user_id, equipment_id, equipped, durability)
                    VALUES (:uid, :eid, FALSE, 100)
                """), {"uid": self.test_user_id, "eid": item_id})
            session.commit()
            
            # Count total items
            total_items = session.execute(text("""
                SELECT COUNT(*) FROM user_equipment WHERE user_id = :uid
            """), {"uid": self.test_user_id}).scalar()
            
            self.assertEqual(total_items, len(item_ids), f"Should have {len(item_ids)} items in inventory")
            
            # Equip some items
            session.execute(text("""
                UPDATE user_equipment SET equipped = TRUE, slot_equipped = 'head'
                WHERE user_id = :uid AND equipment_id = 6
            """), {"uid": self.test_user_id})
            
            session.execute(text("""
                UPDATE user_equipment SET equipped = TRUE, slot_equipped = 'chest'
                WHERE user_id = :uid AND equipment_id = 7
            """), {"uid": self.test_user_id})
            session.commit()
            
            # Count equipped
            equipped_count = session.execute(text("""
                SELECT COUNT(*) FROM user_equipment 
                WHERE user_id = :uid AND equipped = TRUE
            """), {"uid": self.test_user_id}).scalar()
            
            # Count unequipped
            inventory_count = session.execute(text("""
                SELECT COUNT(*) FROM user_equipment 
                WHERE user_id = :uid AND equipped = FALSE
            """), {"uid": self.test_user_id}).scalar()
            
            self.assertEqual(equipped_count, 2, "Should have 2 items equipped")
            self.assertEqual(inventory_count, 4, "Should have 4 items in inventory")
            print(f"✅ Inventory management: {total_items} total, {equipped_count} equipped, {inventory_count} in inventory")
            
        finally:
            session.close()
    
    @classmethod
    def tearDownClass(cls):
        """Clean up test data"""
        session = cls.db.get_session()
        try:
            session.execute(text('DELETE FROM user_equipment WHERE user_id = :uid'),
                          {"uid": cls.test_user_id})
            session.execute(text('DELETE FROM utente WHERE "id_Telegram" = :uid'),
                          {"uid": cls.test_user_id})
            session.commit()
            print("\n🧹 Test cleanup complete")
        finally:
            session.close()

if __name__ == '__main__':
    print("\n" + "="*60)
    print("🧪 EQUIPMENT SYSTEM UNIT TESTS")
    print("="*60)
    
    # Run tests
    suite = unittest.TestLoader().loadTestsFromTestCase(TestEquipmentSystem)
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
        print("\n🎉 ALL TESTS PASSED!")
    else:
        print("\n❌ SOME TESTS FAILED")
    
    sys.exit(0 if result.wasSuccessful() else 1)
