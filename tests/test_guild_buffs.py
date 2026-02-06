import unittest
import datetime
from services.guild_service import GuildService
from database import Database
from models.user import Utente
from models.guild import Guild, GuildMember

class TestGuildBuffs(unittest.TestCase):
    def setUp(self):
        self.guild_service = GuildService()
        self.db = Database()
        self.session = self.db.get_session()
        
        # Clean up
        self.session.query(GuildMember).delete()
        self.session.query(Guild).delete()
        self.session.query(Utente).delete()
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

if __name__ == '__main__':
    unittest.main()
