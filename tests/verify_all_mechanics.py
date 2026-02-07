#!/usr/bin/env python3
import sys
import os
import unittest
import datetime
import random
from sqlalchemy import text

# IMPORTANT: Set TEST_DB before any project imports
os.environ['TEST_DB'] = '1'
sys.path.append(os.getcwd())

from database import Database
from models.user import Utente
from models.pve import Mob
from models.combat import CombatParticipation
from models.resources import Resource, UserResource, RefinedMaterial, UserRefinedMaterial, RefineryDaily, RefineryQueue
from services.user_service import UserService
from services.pve_service import PvEService
from services.crafting_service import CraftingService

class VerifyAllMechanics(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.db = Database()
        # Ensure tables exist (very important for test DB stability)
        cls.db.create_all_tables()
        
        cls.user_service = UserService()
        cls.pve_service = PvEService()
        cls.crafting = CraftingService()
        cls.user_id = 888777
        cls.chat_id = 666555
        
        # Initial cleanup and seeding
        session = cls.db.get_session()
        try:
            # Cleanup
            session.execute(text("DELETE FROM combat_participation WHERE user_id = :uid"), {"uid": cls.user_id})
            session.execute(text("DELETE FROM refinery_queue WHERE user_id = :uid"), {"uid": cls.user_id})
            session.execute(text("DELETE FROM user_refined_materials WHERE user_id = :uid"), {"uid": cls.user_id})
            session.execute(text("DELETE FROM user_resources WHERE user_id = :uid"), {"uid": cls.user_id})
            session.execute(text("DELETE FROM mob WHERE chat_id = :cid"), {"cid": cls.chat_id})
            session.execute(text("DELETE FROM utente WHERE \"id_Telegram\" = :uid"), {"uid": cls.user_id})
            session.commit()
            
            # Create User
            cls.user = Utente(
                id_telegram=cls.user_id,
                nome="VerifyHero",
                username="verifyhero",
                health=500,
                max_health=500,
                current_hp=500,
                mana=200,
                max_mana=200,
                livello=20,
                speed=0,
                livello_selezionato=1,
                stat_points=100
            )
            session.add(cls.user)
            session.flush() # Ensure user exists for Guild FK
            
            # Create Guild (for Refinery Queue FK)
            session.execute(text("DELETE FROM guilds WHERE id = 1"))
            session.execute(text("""
                INSERT INTO guilds (id, name, leader_id, armory_level)
                VALUES (1, 'Test Guild', :uid, 1)
            """), {"uid": cls.user_id})
            
            session.commit()
            
            # Seed minimal required data for refinery if missing
            if session.query(RefinedMaterial).count() == 0:
                session.add(RefinedMaterial(name='Rottami', rarity=1))
                session.add(RefinedMaterial(name='Materiale Pregiato', rarity=2))
                session.add(RefinedMaterial(name='Diamante', rarity=3))
            
            if session.query(Resource).filter_by(name='Ferro Vecchio').count() == 0:
                session.add(Resource(name='Ferro Vecchio', rarity=1))
            if session.query(Resource).filter_by(name='Adamantite').count() == 0:
                session.add(Resource(name='Adamantite', rarity=4))
            
            session.commit()
        finally:
            session.close()

    def setUp(self):
        self.session = self.db.get_session()
        # Refresh user instance to avoid detached session issues
        self.user = self.session.query(Utente).filter_by(id_telegram=self.user_id).first()

    def tearDown(self):
        self.session.rollback()
        self.session.close()

    def test_01_cooldown_speed_scaling(self):
        """Verify speed reduces cooldown correctly"""
        print("\n⏳ Testing Cooldown Scaling...")
        # 0 Speed: Base CD = 60s
        self.user.speed = 0
        self.user.last_attack_time = datetime.datetime.now() - datetime.timedelta(seconds=58)
        self.session.commit()
        
        mob = Mob(name="CDMob", health=1000, max_health=1000, chat_id=self.chat_id)
        self.session.add(mob)
        self.session.commit()
        
        success, msg, _ = self.pve_service.attack_mob(self.user, base_damage=10, mob_id=mob.id, session=self.session)
        self.assertFalse(success, "Should fail CD at 58s with speed 0")
        print(f"✅ Speed 0 blocked attack at 58s as expected")
        
        # High Speed: e.g. 50 Speed -> CD = 60 / (1 + 0.50) = 40s
        self.user.speed = 50
        self.user.last_attack_time = datetime.datetime.now() - datetime.timedelta(seconds=45)
        self.session.commit()
        
        success, msg, _ = self.pve_service.attack_mob(self.user, base_damage=10, mob_id=mob.id, session=self.session)
        self.assertTrue(success, f"Should pass CD at 45s with speed 50. Error: {msg}")
        print(f"✅ Speed 50 allowed attack at 45s as expected")

    def test_02_attack_variety(self):
        """Verify Special and AoE attacks work"""
        print("\n⚔️ Testing Attack Variety...")
        self.user.last_attack_time = datetime.datetime.now() - datetime.timedelta(hours=1)
        self.user.mana = 200
        self.session.commit()
        
        # Special Attack
        res = self.pve_service.use_special_attack(self.user, chat_id=self.chat_id, session=self.session)
        self.assertTrue(res[0], f"Special attack failed: {res[1]}")
        print("✅ Special attack executed")
        
        # AoE Attack
        # Spawn Mobs
        for i in range(3):
            self.session.add(Mob(name=f"AoEMob{i}", health=200, max_health=200, chat_id=self.chat_id))
        self.session.commit()
        
        self.user.last_attack_time = datetime.datetime.now() - datetime.timedelta(hours=1)
        success, msg, extra, events = self.pve_service.attack_aoe(self.user, base_damage=50, chat_id=self.chat_id, session=self.session)
        self.assertTrue(success, f"AoE attack failed: {msg}")
        print("✅ AoE attack executed")

    def test_03_recovery_and_scaling(self):
        """Verify HP scaling and Inn recovery"""
        print("\n❤️ Testing Recovery and Scaling...")
        # Baseline
        self.user_service.recalculate_stats(self.user_id, session=self.session)
        self.session.refresh(self.user)
        initial_hp = self.user.max_health
        
        # Scale
        self.user.stat_points = 10
        self.session.commit()
        self.user_service.allocate_stat_point(self.user, 'health')
        
        self.session.refresh(self.user)
        self.assertEqual(self.user.max_health, initial_hp + 10)
        print(f"✅ HP Scaling works (+1 point = +10 HP)")
        
        # Inn Recovery
        self.user.current_hp = 5
        self.user.resting_since = datetime.datetime.now() - datetime.timedelta(minutes=30)
        self.session.commit()
        
        success, msg = self.user_service.stop_resting(self.user_id, session=self.session)
        self.assertTrue(success)
        self.session.refresh(self.user)
        self.assertGreater(self.user.current_hp, 5)
        print(f"✅ Inn Recovery handled correctly")

    def test_04_refinery_rarity_scaling(self):
        """Verify that higher rarity raw materials yield better results automatically"""
        print("\n💎 Testing Refinery Rarity Scaling...")
        
        # Get raw materials
        m1 = self.session.query(Resource).filter_by(name='Ferro Vecchio').first() # Rarity 1
        m4 = self.session.query(Resource).filter_by(name='Adamantite').first()    # Rarity 4
        
        # Create fake jobs in progress for calculation comparison
        # (We bypass start_refinement to compare the completion logic directly)
        mock_job_low = RefineryQueue(user_id=self.user_id, guild_id=1, resource_id=m1.id, quantity=100, completion_time=datetime.datetime.now(), status='in_progress')
        mock_job_high = RefineryQueue(user_id=self.user_id, guild_id=1, resource_id=m4.id, quantity=100, completion_time=datetime.datetime.now(), status='in_progress')
        
        self.session.add_all([mock_job_low, mock_job_high])
        self.session.commit()
        
        # Process Low Rarity
        res_low = self.crafting.complete_refinement(mock_job_low.id, char_level=10, prof_level=1, armory_level=1)
        self.assertTrue(res_low['success'], f"Low rarity completion failed: {res_low.get('error')}")
        
        # Process High Rarity
        res_high = self.crafting.complete_refinement(mock_job_high.id, char_level=10, prof_level=1, armory_level=1)
        self.assertTrue(res_high['success'], f"High rarity completion failed: {res_high.get('error')}")
        
        total_low = sum(res_low['materials'].values())
        total_high = sum(res_high['materials'].values())
        
        print(f"Low Rarity (1) Yield: {res_low['materials']} (Total: {total_low})")
        print(f"High Rarity (4) Yield: {res_high['materials']} (Total: {total_high})")
        
        # Expected: High rarity yields more total mass (rarity multiplier)
        self.assertGreater(total_high, total_low, "High rarity material should yield more refined items")
        print("✅ Refinery Rarity Scaling verified")

if __name__ == '__main__':
    unittest.main()
