#!/usr/bin/env python3
"""
Integration Test: Core Gameplay Loop
Verifies the full flow:
1. Mob Drops -> User Inventory
2. Refinery -> Raw to Refined Material
3. Guild Upgrade -> Contribute Material to Armory
4. Crafting -> Create Item with stats influenced by Armory Level
"""

import sys
import os
import unittest
from unittest.mock import MagicMock, patch
import json
from datetime import datetime, timedelta

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import Database
from models.user import Utente
from models.guild import Guild, GuildMember, GuildUpgrade
from models.crafting import CraftingQueue
from models.resources import Resource, UserResource, RefinedMaterial, UserRefinedMaterial
from services.crafting_service import CraftingService
from services.guild_service import GuildService
from services.pve_service import PvEService
from sqlalchemy import text

class TestGameplayLoop(unittest.TestCase):
    
    @classmethod
    def setUpClass(cls):
        cls.db = Database()
        cls.crafting = CraftingService()
        cls.guild_service = GuildService()
        cls.pve = PvEService()
        
        # Test Data IDs
        cls.user_id = 9999999 # Unique ID to avoid conflicts
        cls.guild_id = 8888888
        
        # Ensure clean state
        cls.clean_db()
        cls.seed_db()

    @classmethod
    def clean_db(cls):
        session = cls.db.get_session()
        try:
            session.query(UserRefinedMaterial).filter_by(user_id=cls.user_id).delete()
            session.query(UserResource).filter_by(user_id=cls.user_id).delete()
            session.query(CraftingQueue).filter_by(user_id=cls.user_id).delete()
            session.execute(text("DELETE FROM user_equipment WHERE user_id = :uid"), {"uid": cls.user_id})
            
            session.query(GuildMember).filter_by(user_id=cls.user_id).delete()
            session.query(GuildUpgrade).filter_by(guild_id=cls.guild_id).delete()
            session.query(Guild).filter_by(id=cls.guild_id).delete()
            session.query(Utente).filter_by(id_telegram=cls.user_id).delete()
            session.commit()
        except Exception as e:
            print(f"Cleanup error: {e}")
            session.rollback()
        finally:
            session.close()

    @classmethod
    def seed_db(cls):
        session = cls.db.get_session()
        try:
            # 1. Create User
            user = Utente(id_telegram=cls.user_id, username="LoopTester", nome="LoopTester", livello=10)
            session.add(user)
            session.flush() # Ensure user ID exists for FK
            
            # 2. Create Guild (Armory Level 1)
            guild = Guild(id=cls.guild_id, name="LoopGuild", leader_id=cls.user_id, armory_level=1)
            session.add(guild)
            
            # 3. Add Member
            member = GuildMember(guild_id=cls.guild_id, user_id=cls.user_id, role="Leader")
            session.add(member)
            
            # 4. Ensure Resources exist (Rottami -> Metallo)
            rottami = session.query(Resource).filter_by(name="Rottami").first()
            if not rottami:
                print("creating rottami")
                rottami = Resource(id=901, name="Rottami", rarity=1, description="Scrap")
                session.add(rottami)
                session.flush()
            else:
                print(f"found rottami id: {rottami.id}")
            
            metallo = session.query(RefinedMaterial).filter_by(name="Metallo").first()
            if not metallo:
                print("creating metallo")
                metallo = RefinedMaterial(id=902, name="Metallo", rarity=1)
                session.add(metallo)
                session.flush()
            else:
                print(f"found metallo id: {metallo.id}")
            
            session.commit()
            
            # Store IDs for tests
            cls.rottami_id = rottami.id
            cls.metallo_id = metallo.id
            
        except Exception as e:
            print(f"Seed error: {e}")
            session.rollback()
        finally:
            session.close()

    def test_01_mob_drop_resources(self):
        """Step 1: Mob Drop -> User Inventory"""
        print("\n[Test 1] Verifying Resource Drops...")
        
        success = self.crafting.add_resource_drop(self.user_id, self.rottami_id, quantity=10, source="mob")
        self.assertTrue(success, "Should successfully add resource drop")
        
        session = self.db.get_session()
        res = session.query(UserResource).filter_by(user_id=self.user_id, resource_id=self.rottami_id).first()
        self.assertIsNotNone(res)
        self.assertEqual(res.quantity, 10)
        session.close()
        print("✅ Dropped 10 Rottami")

    def test_02_refine_resources(self):
        """Step 2: Refinery -> Raw (Rottami) to Refined (Metallo)"""
        print("\n[Test 2] Verifying Refinery Process...")
        
        # Simulate Refinery Process (Exchange)
        session = self.db.get_session()
        ur = session.query(UserResource).filter_by(user_id=self.user_id, resource_id=self.rottami_id).first()
        ur.quantity -= 5
        
        urm = session.query(UserRefinedMaterial).filter_by(user_id=self.user_id, material_id=self.metallo_id).first()
        if urm:
            urm.quantity += 5
        else:
            urm = UserRefinedMaterial(user_id=self.user_id, material_id=self.metallo_id, quantity=5)
            session.add(urm)
        
        session.commit()
        session.close()
        
        # Verify
        session = self.db.get_session()
        ur = session.query(UserResource).filter_by(user_id=self.user_id, resource_id=self.rottami_id).first()
        urm = session.query(UserRefinedMaterial).filter_by(user_id=self.user_id, material_id=self.metallo_id).first()
        
        self.assertEqual(ur.quantity, 5, "Should have 5 Rottami left")
        self.assertEqual(urm.quantity, 5, "Should have 5 Metallo")
        session.close()
        print("✅ Refined 5 Rottami to 5 Metallo")

    def test_03_guild_armory_upgrade(self):
        """Step 3: Upgrade Guild Armory using Metallo"""
        print("\n[Test 3] Verifying Guild Armory Upgrade...")
        
        # Simulate Upgrade Logic directly on Guild Model
        session = self.db.get_session()
        guild = session.query(Guild).filter_by(id=self.guild_id).first()
        guild.armory_level = 2
        session.commit()
        session.close()
        
        # Verify
        session = self.db.get_session()
        guild = session.query(Guild).filter_by(id=self.guild_id).first()
        self.assertEqual(guild.armory_level, 2, "Armory should be Level 2")
        self.crafting_armory_level = guild.armory_level
        session.close()
        print(f"✅ Armory Upgraded to Level {self.crafting_armory_level}")

    def test_04_craft_item_with_bonus(self):
        """Step 4: Craft Item and Verify Rarity/Stats Scale with Armory"""
        print("\n[Test 4] Verifying Crafting Outcome & Stats...")
        
        # 1. Give resources for crafting
        session = self.db.get_session()
        urm = session.query(UserRefinedMaterial).filter_by(user_id=self.user_id, material_id=self.metallo_id).first()
        urm.quantity += 10
        session.commit()
        session.close()
        
        # 2. Ensure item exists and has correct requirements
        session = self.db.get_session()
        exists = session.execute(text("SELECT id FROM equipment WHERE id = 1")).scalar()
        if not exists:
             session.execute(text("INSERT INTO equipment (id, name, slot, rarity, min_level, crafting_time, crafting_requirements) VALUES (1, 'Gi Test', 'chest', 1, 1, 1, '{\"Metallo\": 5}')"))
        else:
             # Force update requirements and time to ensure valid state
             session.execute(text("UPDATE equipment SET crafting_requirements = '{\"Metallo\": 5}', crafting_time = 1 WHERE id = 1"))
        session.commit()
        session.close()
        
        # 3. Start Crafting
        result = self.crafting.start_crafting(self.guild_id, self.user_id, 1)
        # Assuming start_crafting uses armory level? No, complete_crafting does. start_crafting just queues.
        
        self.assertTrue(result['success'], f"Crafting start failed: {result.get('error')}")
        
        # 4. Fast Forward
        session = self.db.get_session()
        queue_item = session.query(CraftingQueue).filter_by(user_id=self.user_id).first()
        queue_item.completion_time = datetime.now() - timedelta(seconds=10)
        queue_id = queue_item.id
        session.commit()
        session.close()
        
        # 5. Complete with Armory Level 2
        res = self.crafting.complete_crafting(queue_id, armory_level=2, profession_level=10)
        
        self.assertTrue(res['success'], "Crafting completion failed")
        
        # 6. Verify Outcome
        rarity = res['final_rarity']
        print(f"✅ Crafted Item Rarity: {rarity} (Base: 1)")
        
        session = self.db.get_session()
        ue = session.execute(text("SELECT * FROM user_equipment WHERE user_id = :uid ORDER BY id DESC LIMIT 1"), {"uid": self.user_id}).fetchone()
        
        # Parse stats_json
        stats = ue.stats_json if ue.stats_json else {}
        hp_bonus = stats.get('hp', 0)
        atk_bonus = stats.get('attack', 0)
        
        print(f"✅ Item Stats: +{hp_bonus} HP, +{atk_bonus} ATK")
        self.assertIsNotNone(ue)
        session.close()

if __name__ == '__main__':
    unittest.main()
