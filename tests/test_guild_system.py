import unittest
from database import Database
from models.user import Utente
from models.guild import Guild, GuildMember, GuildUpgrade
from services.guild_service import GuildService
from services.user_service import UserService

class TestGuildSystem(unittest.TestCase):
    def setUp(self):
        self.db = Database()
        self.guild_service = GuildService()
        self.user_service = UserService()
        self.u1_id = 111
        self.u2_id = 222
        
        # Clear tables
        session = self.db.get_session()
        session.query(GuildMember).delete()
        session.query(GuildUpgrade).delete()
        session.query(Guild).delete()
        session.query(Utente).filter(Utente.id_telegram.in_([self.u1_id, self.u2_id])).delete()
        
        # Setup users
        self.user1 = Utente(id_telegram=self.u1_id, nome="Leader", livello=10, points=2000)
        self.user2 = Utente(id_telegram=self.u2_id, nome="Member", livello=5, points=500)
        session.add_all([self.user1, self.user2])
        session.commit()
        session.commit()
        session.close()

    def tearDown(self):
        session = self.db.get_session()
        session.query(GuildMember).delete()
        session.query(GuildUpgrade).delete()
        session.query(Guild).delete()
        session.query(Utente).filter(Utente.id_telegram.in_([self.u1_id, self.u2_id])).delete()
        session.commit()
        session.close()

    def test_guild_creation_requirements(self):
        """Verify level and wumpa requirements for guild creation"""
        # Level too low
        success, msg, _ = self.guild_service.create_guild(self.u2_id, "LowLevelGuild")
        self.assertFalse(success)
        self.assertIn("livello 10", msg)
        
        # Not enough wumpa
        session = self.db.get_session()
        u1 = session.query(Utente).filter_by(id_telegram=self.u1_id).first()
        u1.points = 500
        session.commit()
        
        success, msg, _ = self.guild_service.create_guild(self.u1_id, "PoorGuild")
        self.assertFalse(success)
        self.assertIn("1000 Wumpa", msg)
        session.close()

    def test_successful_guild_creation(self):
        """Verify successful guild creation and leader assignment"""
        success, msg, guild_id = self.guild_service.create_guild(self.u1_id, "AlphaGuild")
        self.assertTrue(success)
        
        guild = self.guild_service.get_user_guild(self.u1_id)
        self.assertIsNotNone(guild)
        self.assertEqual(guild['name'], "AlphaGuild")
        self.assertEqual(guild['role'], "Leader")
        
        # Verify wumpa deduction
        session = self.db.get_session()
        u1 = session.query(Utente).filter_by(id_telegram=self.u1_id).first()
        self.assertEqual(u1.points, 1000)
        session.close()

    def test_guild_bank_operations(self):
        """Verify deposit and withdrawal logic"""
        self.guild_service.create_guild(self.u1_id, "BankGuild")
        
        # Deposit
        success, msg = self.guild_service.deposit_wumpa(self.u1_id, 500)
        self.assertTrue(success)
        
        guild = self.guild_service.get_user_guild(self.u1_id)
        self.assertEqual(guild['wumpa_bank'], 500)
        
        # Withdrawal (Leader)
        success, msg = self.guild_service.withdraw_wumpa(self.u1_id, 200)
        self.assertTrue(success)
        
        guild = self.guild_service.get_user_guild(self.u1_id)
        self.assertEqual(guild['wumpa_bank'], 300)
        
        # Withdrawal (Non-leader - should fail as u2 is not in guild yet)
        # But even if u2 was in guild, only leader can withdraw.
        success, msg = self.guild_service.withdraw_wumpa(self.u2_id, 100)
        self.assertFalse(success)

    def test_guild_upgrades(self):
        """Verify inn, armory and village upgrades"""
        self.guild_service.create_guild(self.u1_id, "UpgradeGuild")
        
        # Deposit enough for upgrades
        self.guild_service.deposit_wumpa(self.u1_id, 1000)
        
        # Upgrade Inn (Level 1 -> 2, cost 500)
        success, msg = self.guild_service.upgrade_inn(self.u1_id)
        self.assertTrue(success)
        
        guild = self.guild_service.get_user_guild(self.u1_id)
        self.assertEqual(guild['inn_level'], 2)
        self.assertEqual(guild['wumpa_bank'], 500)
        
        # Try to upgrade village (cost 1000, bank has 500) - should fail
        success, msg = self.guild_service.expand_village(self.u1_id)
        self.assertFalse(success)
        self.assertIn("Servono 1000 Wumpa", msg)

if __name__ == "__main__":
    unittest.main()
