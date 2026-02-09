import unittest
from sqlalchemy import text
import datetime
from services.guild_service import GuildService
from database import Database
from models.user import Utente
from models.guild import Guild, GuildMember
from services.pve_service import PvEService
from services.status_effects import StatusEffect

class TestGuildBuffs(unittest.TestCase):
    def setUp(self):
        self.guild_service = GuildService()
        self.db = Database()
        self.session = self.db.get_session()
        
        # Clean up using CASCADE
        self.session.execute(text("TRUNCATE TABLE utente, guilds, guild_members, crafting_queue, user_refined_materials, parry_states RESTART IDENTITY CASCADE"))
        self.session.commit()
        
        # Create test user
        self.user_id = 12345
        self.user = Utente(id_telegram=self.user_id, game_name="BuffTester", points=1000, livello=10)
        self.session.add(self.user)
        self.session.flush() # Ensure user is in DB before guild
        
        # Create test guild
        self.guild = Guild(name="BuffGuild", leader_id=self.user_id, brewery_level=1, bordello_level=1)
        self.session.add(self.guild)
        self.session.flush()
        
        # Add member
        self.member = GuildMember(guild_id=self.guild.id, user_id=self.user_id, role="Leader")
        self.session.add(self.member)
        self.session.commit()

    def tearDown(self):
        self.session.close()

    def test_brewery_potion_bonus_duration(self):
        # Initial: no bonus
        bonus = self.guild_service.get_potion_bonus(self.user_id)
        self.assertEqual(bonus, 1.0)
        
        # Drink beer
        self.guild_service.buy_craft_beer(self.user_id)
        
        # Bonus should be active
        bonus = self.guild_service.get_potion_bonus(self.user_id)
        self.assertGreater(bonus, 1.0) # Lv 1 should be 1.2
        
        # Mock time forward 31 minutes
        user = self.session.query(Utente).filter_by(id_telegram=self.user_id).first()
        user.last_beer_usage = datetime.datetime.now() - datetime.timedelta(minutes=31)
        self.session.commit()
        
        # Bonus should be gone
        bonus = self.guild_service.get_potion_bonus(self.user_id)
        self.assertEqual(bonus, 1.0)

    def test_bordello_vigore_duration(self):
        # Initial: no multi (1.0)
        mult = self.guild_service.get_mana_cost_multiplier(self.user_id)
        self.assertEqual(mult, 1.0)
        
        # Visit brothel
        self.guild_service.apply_vigore_bonus(self.user_id)
        
        # Bonus should be active (0.5)
        mult = self.guild_service.get_mana_cost_multiplier(self.user_id)
        self.assertEqual(mult, 0.5)
        
        # Check vigore_until is exactly 30 mins from now
        user = self.session.query(Utente).filter_by(id_telegram=self.user_id).first()
        expected_until = datetime.datetime.now() + datetime.timedelta(minutes=30)
        self.assertLess(abs((user.vigore_until - expected_until).total_seconds()), 10) # Within 10s
        
        # Mock time forward 31 minutes
        user.vigore_until = datetime.datetime.now() - datetime.timedelta(minutes=1)
        self.session.commit()
        
        # Bonus should be gone
        mult = self.guild_service.get_mana_cost_multiplier(self.user_id)
        self.assertEqual(mult, 1.0)

    def test_bordello_mana_reduction(self):
        """Verify Bordello significantly reduces mana costs"""
        user_id = 991
        user = Utente(id_telegram=user_id, nome="ManaTester", points=1000, livello=10, mana=100, max_mana=100)
        self.session.add(user)
        self.session.flush()

        # Create Guild with Level 5 Bordello (Max reduction)
        guild = Guild(name="ManaGuild", leader_id=user_id, bordello_level=5)
        self.session.add(guild)
        self.session.flush()
        
        member = GuildMember(guild_id=guild.id, user_id=user_id, role="Leader")
        self.session.add(member)
        self.session.commit()

        # Base cost should be 1.0 multiplier
        base_mult = self.guild_service.get_mana_cost_multiplier(user_id)
        self.assertEqual(base_mult, 1.0, "Base multiplier should be 1.0 without buff")

        # Apply Vigore Bonus (Bordello visit)
        success, msg = self.guild_service.apply_vigore_bonus(user_id)
        self.assertTrue(success)
        
        # Check multiplier reduction
        # Lv 5 Bordello -> 50% discount -> 0.5 multiplier? Or does it scale?
        # Let's check the logic: 1.0 - (level * 0.1) -> Lv 5 = 0.5
        new_mult = self.guild_service.get_mana_cost_multiplier(user_id)
        self.assertEqual(new_mult, 0.5, "Level 5 Bordello should give 0.5x cost multiplier")

    def test_tavern_buff_application(self):
        """Verify Tavern beer gives actual stats"""
        user_id = 992
        user = Utente(id_telegram=user_id, nome="BeerTester", points=1000, livello=10, allocated_damage=100)
        self.session.add(user)
        self.session.flush()

        # Create Guild with Level 10 Brewery
        guild = Guild(name="BeerGuild", leader_id=user_id, brewery_level=10)
        self.session.add(guild)
        self.session.flush()
        
        member = GuildMember(guild_id=guild.id, user_id=user_id, role="Leader")
        self.session.add(member)
        self.session.commit()

        # Usage
        success, msg = self.guild_service.buy_craft_beer(user_id)
        self.assertTrue(success)
        self.assertIn("bevuto una Birra Artigianale", msg)

        # Verify Potion Bonus Multiplier
        # Formula: 15 + (brew_level * 5)
        # Lv 10 Brewery -> 15 + 50 = 65% -> 1.65 multiplier
        bonus = self.guild_service.get_potion_bonus(user_id)
        self.assertAlmostEqual(bonus, 1.65, places=2, msg="Level 10 Brewery should give 65% bonus (1.65x)")
        
        # Verify user update
        updated_user = self.session.query(Utente).filter_by(id_telegram=user_id).first()
        self.assertIsNotNone(updated_user.last_beer_usage)

if __name__ == '__main__':
    unittest.main()
