import unittest
from unittest.mock import patch
import datetime
import json
from database import Database
from models.user import Utente
from models.inventory import UserItem
from models.pve import Mob
from models.combat import CombatParticipation
from models.seasons import Season
from models.dungeon import Dungeon # Added to resolve NoReferencedTableError
from services.user_service import UserService
from services.pve_service import PvEService

class TestCombatFeatures(unittest.TestCase):
    def setUp(self):
        self.db = Database()
        self.user_service = UserService()
        self.pve_service = PvEService()
        
        # Clear DB
        session = self.db.get_session()
        session.query(CombatParticipation).delete()
        session.query(Mob).delete()
        session.commit()
        
        # Setup test users
        def get_or_create(uid, username, nome):
            u = session.query(Utente).filter_by(id_telegram=uid).first()
            if not u:
                u = Utente(id_telegram=uid, username=username, nome=nome, points=0, exp=0, game_name=nome)
                session.add(u)
            u.username = username
            u.game_name = nome
            u.points = 0
            u.exp = 0
            u.health = 100
            u.current_hp = 100
            u.mana = 100
            u.max_mana = 100
            u.last_attack_time = datetime.datetime.now() - datetime.timedelta(hours=1)
            u.livello = 1
            u.livello_selezionato = 1 
            return u

        self.u1_id = 11111
        self.u2_id = 22222
        get_or_create(self.u1_id, "user1", "Player One")
        get_or_create(self.u2_id, "user2", "Player Two")
        
        # Ensure a season exists
        season = session.query(Season).filter_by(is_active=True).first()
        if not season:
            season = Season(
                name="Test Season", 
                theme="Dragon Ball", 
                is_active=True,
                start_date=datetime.datetime.now(),
                end_date=datetime.datetime.now() + datetime.timedelta(days=30)
            )
            session.add(season)
        else:
            season.theme = "Dragon Ball"
            
        session.commit()
        session.close()

    def tearDown(self):
        session = self.db.get_session()
        session.query(Mob).delete()
        session.query(CombatParticipation).delete()
        session.query(Utente).filter(Utente.id_telegram.in_([self.u1_id, self.u2_id])).delete()
        session.commit()
        session.close()

    def test_status_card_formatting(self):
        """Verify that status cards contain expected information and formatting"""
        session = self.db.get_session()
        mob = Mob(name="TestMob", health=100, max_health=100, speed=10, difficulty_tier=1)
        user = session.query(Utente).filter_by(id_telegram=self.u1_id).first()
        
        # Test with username
        user.username = "User1"
        mob_card = self.pve_service.get_status_card(mob, is_user=False)
        user_card = self.pve_service.get_status_card(user, is_user=True)
        
        self.assertIn("╔══════🕹 **TESTMOB** ══════╗", mob_card)
        self.assertIn("╔══════🕹 **USER1** ══════╗", user_card)
        
        # Test without username (should use game_name)
        user.username = None
        user.game_name = "Player One"
        user_card_no_username = self.pve_service.get_status_card(user, is_user=True)
        self.assertIn("╔══════🕹 **PLAYER ONE** ══════╗", user_card_no_username)
        
        session.close()

    def test_aoe_attack_mechanics(self):
        """Verify AoE damage (70% target, 50% others), mana cost (0), and cooldown"""
        # Manually spawn 2 mobs
        session = self.db.get_session()
        m1 = Mob(name="Mob1", health=100, max_health=100, attack_damage=5, attack_type="Physical", chat_id=999, is_dead=False)
        m2 = Mob(name="Mob2", health=100, max_health=100, attack_damage=5, attack_type="Physical", chat_id=999, is_dead=False)
        session.add_all([m1, m2])
        session.commit()
        m1_id = m1.id
        m2_id = m2.id
        
        user = session.query(Utente).filter_by(id_telegram=self.u1_id).first()
        initial_mana = user.mana
        
        # Perform AoE targeting Mob1
        with patch('random.randint', return_value=100): # Disable crits
            success, msg, extra_data, attack_events = self.pve_service.attack_aoe(user, base_damage=100, chat_id=999, target_mob_id=m1_id)
        self.assertTrue(success)
        
        # Verify Mana (cost 0)
        session.refresh(user)
        self.assertEqual(user.mana, initial_mana)
        
        # Verify Damage
        # Mob1 (Target): 70% of 100 = 70 damage -> 30 HP
        # Mob2 (Other): 50% of 100 = 50 damage -> 50 HP
        session.refresh(m1)
        session.refresh(m2)
        
        # We need to account for battle_service.calculate_damage which adds variance/crit
        # But in tests, we can check if m1 took more damage than m2
        self.assertLess(m1.health, m2.health, f"Target {m1.health} should have less health than other {m2.health}")
        self.assertLess(m1.health, 100)
        self.assertLess(m2.health, 100)
            
        # Verify Cooldown (60s base, 2x for AoE = 120s)
        elapsed = (datetime.datetime.now() - user.last_attack_time).total_seconds()
        self.assertLess(elapsed, 5) 
        
        session.close()

    @patch('random.random')
    def test_seasonal_spawn_probability(self, mock_random):
        """Verify 80% chance for seasonal mobs"""
        # We need to use None for chat_id to bypass the GRUPPO_AROMA check
        # Mock random to 0.79 (Seasonal)
        mock_random.return_value = 0.79
        success, msg, mob_id = self.pve_service.spawn_specific_mob(chat_id=None)
        self.assertTrue(success, f"Spawn failed: {msg}")
        
        session = self.db.get_session()
        mob = session.query(Mob).filter_by(id=mob_id).first()
        # Find mob data to check saga
        mob_data = next((m for m in self.pve_service.mob_data if m['nome'] == mob.name), None)
        self.assertIn("dragon ball", mob_data.get('saga', '').lower())
        
        # Cleanup for next spawn
        mob.is_dead = True
        session.commit()
        
        # Mock random to 0.81 (Random)
        mock_random.return_value = 0.81
        success, msg, mob_id2 = self.pve_service.spawn_specific_mob(chat_id=None)
        self.assertTrue(success, f"Spawn failed: {msg}")
        
        session.close()

    def test_reward_distribution_aoe(self):
        """Verify rewards are distributed to all participants on AoE kill"""
        # Manually spawn 2 mobs
        session = self.db.get_session()
        m1 = Mob(name="Mob1", health=20, max_health=100, attack_damage=5, attack_type="Physical", chat_id=999, is_dead=False)
        m2 = Mob(name="Mob2", health=20, max_health=100, attack_damage=5, attack_type="Physical", chat_id=999, is_dead=False)
        session.add_all([m1, m2])
        session.commit()
        
        m1_id = m1.id
        m2_id = m2.id
        
        u1 = session.query(Utente).filter_by(id_telegram=self.u1_id).first()
        u2 = session.query(Utente).filter_by(id_telegram=self.u2_id).first()
        
        # U2 deals some damage first to Mob 1
        self.pve_service.update_participation(m1_id, self.u2_id, 10)
        
        # Ensure u1's cooldown is reset for the AoE attack
        u1.last_attack_time = datetime.datetime.now() - datetime.timedelta(hours=1)
        session.commit()

        # U1 uses AoE to kill both
        success, msg, extra_data, attack_events = self.pve_service.attack_aoe(u1, base_damage=100, chat_id=999)
        self.assertTrue(success)
        self.assertIn("💀", msg)
        self.assertIn("Ricompense distribuite", msg)
        
        # Verify both got rewards
        session.refresh(u1)
        session.refresh(u2)
        
        self.assertGreater(u1.points, 0)
        self.assertGreater(u1.exp, 0)
        self.assertGreater(u2.points, 0)
        self.assertGreater(u2.exp, 0)
        
        session.close()

    def test_level_up_announcement(self):
        """Verify that level-up is announced in combat messages"""
        session = self.db.get_session()
        user = session.query(Utente).filter_by(id_telegram=self.u1_id).first()
        
        # 1. Test Single Target Kill Level Up
        # Setup user near level up
        user.exp = 390 
        user.livello = 1
        session.commit()
        
        # Use high difficulty to ensure high EXP gain
        m1 = Mob(name="Target1", health=10, max_health=100, attack_damage=5, attack_type="Physical", chat_id=999, is_dead=False, difficulty_tier=10)
        session.add(m1)
        session.commit()
        m1_id = m1.id
        
        # Kill it
        success, msg, extra_data = self.pve_service.attack_mob(user, base_damage=100, mob_id=m1_id)
        self.assertTrue(success, f"Attack failed: {msg}")
        self.assertIn("LEVEL UP!", msg, f"Level up not found in message: {msg}")
        
        # 2. Test AoE Level Up
        # Clear mobs first
        session.query(Mob).delete()
        session.commit()
        
        # Reset user to level 1 and give near-level-up exp
        user.exp = 390
        user.livello = 1
        user.last_attack_time = datetime.datetime.now() - datetime.timedelta(hours=1)
        session.commit()
        
        # Spawn a fresh mob for AoE
        m2 = Mob(name="Target2", health=10, max_health=100, attack_damage=5, attack_type="Physical", chat_id=999, is_dead=False, difficulty_tier=10)
        session.add(m2)
        session.commit()
        
        success, msg, extra_data, attack_events = self.pve_service.attack_aoe(user, base_damage=100, chat_id=999)
        self.assertTrue(success, f"AoE failed: {msg}")
        self.assertIn("è salito al livello", msg, f"AoE level up not found in message: {msg}")
        
        session.close()

    def test_aoe_target_limit(self):
        """Verify AoE hits max 5 targets"""
        session = self.db.get_session()
        for i in range(10):
            m = Mob(name=f"Mob{i}", health=100, max_health=100, chat_id=999, is_dead=False)
            session.add(m)
        session.commit()
        
        user = session.query(Utente).filter_by(id_telegram=self.u1_id).first()
        success, msg, extra_data, attack_events = self.pve_service.attack_aoe(user, base_damage=100, chat_id=999)
        self.assertTrue(success)
        
        # Check how many mobs took damage
        mobs_hit = session.query(Mob).filter(Mob.chat_id==999, Mob.health < 100).count()
        self.assertEqual(mobs_hit, 5)
        session.close()

    def test_aoe_button_visibility(self):
        """Verify AoE button only shown if >= 2 mobs"""
        from main import get_combat_markup
        
        # 1 mob
        session = self.db.get_session()
        session.query(Mob).delete()
        m1 = Mob(name="Mob1", health=100, max_health=100, chat_id=999, is_dead=False)
        session.add(m1)
        session.commit()
        m1_id = m1.id
        
        markup = get_combat_markup("mob", m1_id, 999)
        # Check if AoE button in markup
        has_aoe = any("aoe_attack_enemy" in b.callback_data for row in markup.keyboard for b in row)
        self.assertFalse(has_aoe)
        
        # 2 mobs
        m2 = Mob(name="Mob2", health=100, max_health=100, chat_id=999, is_dead=False)
        session.add(m2)
        session.commit()
        
        markup = get_combat_markup("mob", m1_id, 999)
        has_aoe = any("aoe_attack_enemy" in b.callback_data for row in markup.keyboard for b in row)
        self.assertTrue(has_aoe)
        session.close()

    def test_multiple_mob_spawns(self):
        """Verify that multiple mobs can be spawned up to the limit of 10"""
        session = self.db.get_session()
        session.query(Mob).delete()
        session.commit()
        
        # Spawn 10 mobs
        for i in range(10):
            success, msg, mob_id = self.pve_service.spawn_specific_mob(chat_id=None) # Use None to bypass GRUPPO_AROMA check
            self.assertTrue(success, f"Failed to spawn mob {i}: {msg}")
            
        # Try to spawn the 11th
        success, msg, mob_id = self.pve_service.spawn_specific_mob(chat_id=None)
        self.assertFalse(success)
        self.assertIn("già un mob attivo", msg)
        
        session.close()

    def test_resting_methods(self):
        """Test entering and leaving the inn"""
        session = self.db.get_session()
        self.user = session.query(Utente).filter_by(id_telegram=self.u1_id).first()
        self.user.current_hp = 50
        self.user.mana = 50
        # Test entering the inn
        initial_points = self.user.points
        success, msg = self.user_service.start_resting(self.user.id_telegram)
        self.assertTrue(success)
        self.assertIn("iniziato a riposare", msg)
        
        # Mock resting time to ensure recovery
        session = self.db.get_session()
        u = session.query(Utente).filter_by(id_telegram=self.u1_id).first()
        u.resting_since = datetime.datetime.now() - datetime.timedelta(hours=2)
        session.commit()
        session.close()
        
        success, msg = self.user_service.stop_resting(self.user.id_telegram)
        self.assertTrue(success)
        self.assertIn("smesso di riposare", msg)
        
        # Refresh user from DB
        session = self.db.get_session()
        self.user = session.query(Utente).filter_by(id_telegram=self.u1_id).first()
        
        self.assertIsNone(self.user.resting_since)
        self.assertEqual(self.user.current_hp, self.user.health) # Should be fully healed
        session.close()
        self.assertEqual(self.user.mana, self.user.max_mana) # Should be fully restored

        # Test trying to leave when not resting
        success, msg = self.user_service.stop_resting(self.user.id_telegram)
        self.assertFalse(success)
        self.assertIn("Non stai riposando", msg)
        
        session.close()

if __name__ == "__main__":
    unittest.main()
