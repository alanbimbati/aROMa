
import unittest
from unittest.mock import MagicMock, patch
from services.guild_service import GuildService
from services.user_service import UserService
from models.guild import Guild, GuildMember
from models.user import Utente

class TestGuildSystem(unittest.TestCase):
    def setUp(self):
        self.guild_service = GuildService()
        self.user_service = UserService()
        
    def test_join_guild(self):
        # Mock session
        session = MagicMock()
        patcher = patch.object(self.guild_service.db, 'get_session', return_value=session)
        patcher.start()
        self.addCleanup(patcher.stop)
        
        # Mock existing guild
        guild = Guild(id=1, name="TestGuild", member_limit=5)
        # We need to ensure filter_by(id=...).first() returns this guild
        # and filter_by(guild_id=...).count() returns 1
        
        # Setup side_effect for query
        def query_side_effect(*args, **kwargs):
            model = args[0] if args else None
            query = MagicMock()
            if model == Guild:
                query.filter_by.return_value.first.return_value = guild
            elif model == GuildMember:
                query.filter_by.return_value.first.return_value = None # Not in guild
                query.filter_by.return_value.count.return_value = 1 # 1 member
            return query
            
        session.query.side_effect = query_side_effect
        
        # Test join
        success, msg = self.guild_service.join_guild(user_id=12345, guild_id=1)
        self.assertTrue(success, f"Join failed with message: {msg}")
        self.assertIn("Benvenuto", msg)
        
    def test_upgrade_building(self):
        # Mock session
        session = MagicMock()
        patcher = patch.object(self.guild_service.db, 'get_session', return_value=session)
        patcher.start()
        self.addCleanup(patcher.stop)
        
        # Mock leader member
        member = GuildMember(guild_id=1, user_id=111, role="Leader")
        
        # Mock guild with funds
        guild = Guild(id=1, name="TestGuild", inn_level=1, wumpa_bank=10000)
        
        def query_side_effect(*args, **kwargs):
            model = args[0] if args else None
            query = MagicMock()
            if model == GuildMember:
                query.filter_by.return_value.first.return_value = member
            elif model == Guild:
                query.filter_by.return_value.first.return_value = guild
            return query
            
        session.query.side_effect = query_side_effect
        
        # Test upgrade inn
        success, msg = self.guild_service.upgrade_inn(leader_id=111)
        self.assertTrue(success, f"Upgrade failed with message: {msg}")
        self.assertEqual(guild.inn_level, 2)
        self.assertEqual(guild.wumpa_bank, 9500) # 10000 - 500

if __name__ == '__main__':
    unittest.main()
