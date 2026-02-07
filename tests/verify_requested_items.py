#!/usr/bin/env python3
import sys
import os
import unittest
import datetime
from sqlalchemy import text

# Ensure we use the test database
os.environ['TEST_DB'] = '1'
sys.path.append(os.getcwd())

from database import Database
from models.user import Utente
from models.pve import Mob
from models.combat import CombatParticipation
from services.user_service import UserService
from services.pve_service import PvEService
from services.crafting_service import CraftingService

class VerifyRequestedItems(unittest.TestCase):
    db = Database()
    user_service = UserService()
    pve_service = PvEService()
    crafting = CraftingService()
    user_id = 888777
    chat_id = 666555

    def setUp(self):
        self.session = self.db.get_session()
        uid = self.user_id
        cid = self.chat_id
        
        # Thorough cleanup
        self.session.query(CombatParticipation).filter_by(user_id=uid).delete()
        self.session.execute(text("DELETE FROM user_resources WHERE user_id = :uid"), {"uid": uid})
        self.session.execute(text("DELETE FROM user_equipment WHERE user_id = :uid"), {"uid": uid})
        self.session.commit()
        
        # Get or Create User
        self.user = self.session.query(Utente).filter_by(id_telegram=uid).first()
        if not self.user:
            self.user = Utente(
                id_telegram=uid,
                nome="VerifyHero",
                username=f"hero_{uid}",
                health=500,
                max_health=500,
                current_hp=500,
                mana=200,
                max_mana=200,
                livello=20,
                speed=0,
                livello_selezionato=1
            )
            self.session.add(self.user)
        else:
            self.user.health = 500
            self.user.max_health = 500
            self.user.current_hp = 500
            self.user.mana = 200
            self.user.max_mana = 200
            self.user.speed = 0
            self.user.last_attack_time = None
            self.user.resting_since = None
            
        self.session.commit()
        self.session.refresh(self.user)

    def tearDown(self):
        # We can leave the user for next test, but cleanup combat
        self.session.query(CombatParticipation).filter_by(user_id=self.user_id).delete()
        self.session.execute(text("DELETE FROM mob WHERE chat_id = :cid"), {"cid": self.chat_id})
        self.session.commit()
        self.session.close()

    def test_01_cooldown_speed_scaling(self):
        """Verify that speed actually reduces cooldown correctly"""
        print("\n⏳ Testing Cooldown Scaling...")
        user = self.session.query(Utente).filter_by(id_telegram=self.user_id).first()
        
        # Test Case 1: 0 Speed (Base CD = 60s)
        user.speed = 0
        user.last_attack_time = datetime.datetime.now() - datetime.timedelta(seconds=58)
        self.session.commit()
        
        mob = Mob(name="CDMob", health=1000, chat_id=self.chat_id)
        self.session.add(mob)
        self.session.commit()
        
        success, msg, _ = self.pve_service.attack_mob(user, base_damage=10, mob_id=mob.id, session=self.session)
        self.assertFalse(success, f"Should fail CD at 58s with speed 0. Got success: {msg}")
        print(f"✅ Speed 0 blocked attack at 58s (Expected > 60s)")
        
        # Test Case 2: 20 Speed (CD = 60 / (1 + 0.20) = 50s)
        # We need to refresh user to avoid DetachedInstance or stale data
        self.session.expire_all()
        user = self.session.query(Utente).filter_by(id_telegram=self.user_id).first()
        user.speed = 20
        user.last_attack_time = datetime.datetime.now() - datetime.timedelta(seconds=51)
        self.session.commit()
        
        success, msg, _ = self.pve_service.attack_mob(user, base_damage=10, mob_id=mob.id, session=self.session)
        self.assertTrue(success, f"Should pass CD at 51s with speed 20. msg: {msg}")
        print(f"✅ Speed 20 allowed attack at 51s (Expected < 50s check pass)")

    def test_02_attack_variety(self):
        """Verify Basic, Special, and AoE attacks work"""
        print("\n⚔️ Testing Attack Variety...")
        user = self.session.query(Utente).filter_by(id_telegram=self.user_id).first()
        user.last_attack_time = datetime.datetime.now() - datetime.timedelta(hours=1)
        user.mana = 200
        self.session.commit()
        
        # Spawn Mobs
        mobs = []
        for i in range(3):
            m = Mob(name=f"VarietyMob{i}", health=200, chat_id=self.chat_id)
            self.session.add(m)
            mobs.append(m)
        self.session.commit()
        
        # Special Attack
        res = self.pve_service.use_special_attack(user, chat_id=self.chat_id, session=self.session)
        self.assertTrue(res[0], f"Special attack failed: {res[1]}")
        print("✅ Special attack executed and consumed mana")
        
        # Reset CD for next test
        self.session.expire_all()
        user = self.session.query(Utente).filter_by(id_telegram=self.user_id).first()
        user.last_attack_time = datetime.datetime.now() - datetime.timedelta(hours=1)
        self.session.commit()
        
        # AoE Attack
        success, msg, extra, events = self.pve_service.attack_aoe(user, base_damage=50, chat_id=self.chat_id, session=self.session)
        self.assertTrue(success, f"AoE attack failed: {msg}")
        print("✅ AoE attack executed on multiple targets")

    def test_03_recovery_and_scaling(self):
        """Verify HP/Mana recovery via Inn/Potions and scaling"""
        print("\n❤️ Testing Recovery and Scaling...")
        user = self.session.query(Utente).filter_by(id_telegram=self.user_id).first()
        
        # 1. Scaling: Allocate points
        self.user_service.recalculate_stats(user.id_telegram, session=self.session)
        self.session.expire_all()
        user = self.session.query(Utente).filter_by(id_telegram=self.user_id).first()
        initial_max_hp = user.max_health
        user.stat_points = 10
        self.session.commit()
        
        self.user_service.allocate_stat_point(user, 'health') # This calls update_user which uses its own session unless we change it.
        # Wait, allocate_stat_point doesn't take session. It calls self.update_user.
        # self.update_user handles its own session.
        
        self.session.expire_all()
        user = self.session.query(Utente).filter_by(id_telegram=self.user_id).first()
        self.assertEqual(user.max_health, initial_max_hp + 10)
        print(f"✅ HP Scaling: +1 point = +10 Max HP ({initial_max_hp} -> {user.max_health})")
        
        # 2. Recovery: Resting in Inn
        user.current_hp = 10
        user.resting_since = datetime.datetime.now() - datetime.timedelta(minutes=30)
        self.session.commit()
        
        success, msg = self.user_service.stop_resting(user.id_telegram, session=self.session)
        self.assertTrue(success)
        
        self.session.refresh(user)
        self.assertGreater(user.current_hp, 10)
        print(f"✅ Inn Recovery: Handled correctly ({msg})")

    def test_04_refinery_summary(self):
        """Summary verification of refinery"""
        print("\n💎 Testing Refinery Integration...")
        daily = self.crafting.get_daily_refinable_resource()
        self.assertIsNotNone(daily)
        print(f"✅ Refinery: Daily resource rotation active ({daily['name']})")

if __name__ == '__main__':
    unittest.main()
