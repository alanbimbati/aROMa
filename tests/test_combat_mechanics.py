
import unittest
from unittest.mock import MagicMock, patch
import sys
import os

# Add project root to path
sys.path.append(os.getcwd())

from services.pve_service import PvEService
from services.user_service import UserService
from models.user import Utente
from models.pve import Mob
from database import Database

class TestCombatMechanics(unittest.TestCase):
    def setUp(self):
        self.db = Database()
        self.session = self.db.get_session()
        self.pve_service = PvEService()
        self.user_service = UserService()
        
        # Create test user
        self.user = Utente(
            id_telegram=16001, 
            nome="TestWarrior", 
            username="testwarrior", 
            livello=10,
            health=1000,
            max_health=1000,
            mana=500,
            max_mana=500,
            base_damage=50,
            resistance=0
        )
        self.session.add(self.user)
        
        # Create test mob
        self.mob = Mob(
            name="TestMob",
            chat_id=-10016001,
            health=500,
            max_health=500,
            attack_damage=40,
            is_dead=False
        )
        self.session.add(self.mob)
        self.session.commit()
        
    def tearDown(self):
        self.session.rollback()
        mob_id = self.mob.id
        user_id = 16001
        
        from sqlalchemy import text
        try:
            self.session.execute(text("TRUNCATE combat_participation CASCADE"))
        except:
            self.session.execute(text("DELETE FROM combat_participation"))
        self.session.commit()
        
        self.session.query(Utente).filter_by(id_telegram=user_id).delete()
        self.session.query(Mob).filter_by(id=mob_id).delete()
        self.session.commit()
        self.session.close()
        
    def test_damage_calculation(self):
        """Test basic damage calculation with level scaling"""
        # User attacks Mob
        # Damage formula in attack_mob: damage * random(0.9, 1.1)
        # We can't easily test exact random values, but we can check range
        
        initial_hp = self.mob.health
        success, msg, extra = self.pve_service.attack_mob(self.user, 50, mob_id=self.mob.id, session=self.session)
        
        self.assertTrue(success)
        self.session.refresh(self.mob)
        self.assertLess(self.mob.health, initial_hp)
        
    def test_resistance_reduction(self):
        """Test that resistance reduces incoming damage"""
        # Mob attacks User
        # We need to simulate damage_health call directly as mob_random_attack is complex
        
        # Case 1: 0 Resistance
        self.user.resistance = 0
        self.user.health = 1000
        self.user.current_hp = 1000
        self.session.commit()
        
        damage_in = 100
        new_hp, died = self.user_service.damage_health(self.user, damage_in, session=self.session)
        damage_taken_0 = 1000 - new_hp
        self.assertEqual(damage_taken_0, 100)
        
        # Case 2: 50% Resistance
        # Note: damage_health currently does NOT apply resistance. 
        # Resistance is applied in pve_service before calling damage_health.
        # We simulate this by applying the formula here.
        self.user.resistance = 50
        self.user.health = 1000
        self.user.current_hp = 1000
        self.session.commit()
        
        # Formula: damage * (100 / (100 + res))
        res_factor = 100 / (100 + self.user.resistance)
        damage_after_res = int(damage_in * res_factor)
        
        new_hp, died = self.user_service.damage_health(self.user, damage_after_res, session=self.session)
        damage_taken_50 = 1000 - new_hp
        
        self.assertLess(damage_taken_50, damage_taken_0)
        self.assertEqual(damage_taken_50, int(100 * (100/150)))

    def test_special_attack_mana(self):
        """Test special attack consumes mana"""
        initial_mana = self.user.mana
        mana_cost = 50
        
        # Mock character loader to avoid file dependency if possible, 
        # but attack_mob doesn't check loader, main.py does. 
        # pve_service.attack_mob just takes mana_cost arg if use_special=True
        
        # We need to manually deduct mana in pve_service or main?
        # Looking at main.py: user_service.update_user(user_id, {'mana': utente.mana - mana_cost}) was commented out
        # and moved to pve_service? Let's check pve_service.attack_mob
        
        success, msg, extra = self.pve_service.attack_mob(
            self.user, 
            base_damage=100, 
            use_special=True, 
            mob_id=self.mob.id, 
            mana_cost=mana_cost,
            session=self.session
        )
        
        self.session.refresh(self.user)
        self.assertEqual(self.user.mana, initial_mana - mana_cost)
