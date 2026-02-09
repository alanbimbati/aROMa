import unittest
from sqlalchemy import text
import datetime
import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from database import Database, Base
from models.user import Utente
from models.guild import Guild, GuildMember
from services.user_service import UserService
from services.guild_service import GuildService
from services.pve_service import PvEService
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

class TestGuildExpansion(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.db = Database()
        cls.user_service = UserService()
        cls.guild_service = GuildService()
        cls.pve_service = PvEService()
        
        cls.u1_id = 999001
        cls.u2_id = 999002

    def setUp(self):
        session = self.db.get_session()
        # Clean up using CASCADE to handle all dependencies
        session.execute(text("TRUNCATE TABLE utente, guilds, guild_members, crafting_queue, user_refined_materials, parry_states RESTART IDENTITY CASCADE"))
        session.commit()
        
        u1 = Utente(id_telegram=self.u1_id, nome="Leader", livello=10, points=5000, health=100, max_health=100, current_hp=50, mana=20, max_mana=100)
        u2 = Utente(id_telegram=self.u2_id, nome="Member", livello=5, points=1000, health=100, max_health=100, current_hp=50, mana=20, max_mana=100)
        session.add(u1)
        session.add(u2)
        session.commit()
        session.close()

    def test_public_inn_resting(self):
        # Start resting
        success, msg = self.user_service.start_resting(self.u1_id)
        self.assertTrue(success)
        
        session = self.db.get_session()
        user = session.query(Utente).filter_by(id_telegram=self.u1_id).first()
        # Mock resting_since to 10 minutes ago
        user.resting_since = datetime.datetime.now() - datetime.timedelta(minutes=10)
        session.commit()
        
        status = self.user_service.get_resting_status(self.u1_id)
        self.assertEqual(status['minutes'], 10)
        self.assertEqual(status['hp'], 10)
        self.assertEqual(status['mana'], 10)
        
        # Stop resting
        success, msg = self.user_service.stop_resting(self.u1_id)
        self.assertTrue(success)
        
        user = session.query(Utente).filter_by(id_telegram=self.u1_id).first()
        self.assertEqual(user.current_hp, 60)
        self.assertEqual(user.mana, 30)
        self.assertIsNone(user.resting_since)
        session.close()

    def test_guild_list_and_members(self):
        # Create guild
        self.guild_service.create_guild(self.u1_id, "ExpansionGuild")
        
        guilds = self.guild_service.get_guilds_list()
        self.assertEqual(len(guilds), 1)
        self.assertEqual(guilds[0]['name'], "ExpansionGuild")
        
        guild_id = guilds[0]['id']
        members = self.guild_service.get_guild_members(guild_id)
        self.assertEqual(len(members), 1)
        self.assertEqual(members[0]['user_id'], self.u1_id)

    def test_bordello_and_vigore(self):
        # Ensure guild exists
        self.guild_service.create_guild(self.u1_id, "BordelloGuild")
        
        # Deposit wumpa for upgrade
        self.guild_service.deposit_wumpa(self.u1_id, 2000)
        
        # Upgrade bordello
        success, msg = self.guild_service.upgrade_bordello(self.u1_id)
        self.assertTrue(success)
        
        # Apply vigore bonus
        success, msg = self.guild_service.apply_vigore_bonus(self.u1_id)
        self.assertTrue(success)
        
        # Check multiplier
        multiplier = self.guild_service.get_mana_cost_multiplier(self.u1_id)
        self.assertEqual(multiplier, 0.5)

if __name__ == '__main__':
    unittest.main()
