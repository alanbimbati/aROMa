
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
        
        # Mock guild with funds (locanda lv1→2 costa 5000)
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
        
        # Test upgrade inn (lv1→2 = 5000 wumpa)
        success, msg = self.guild_service.upgrade_inn(leader_id=111)
        self.assertTrue(success, f"Upgrade failed with message: {msg}")
        self.assertEqual(guild.inn_level, 2)
        self.assertEqual(guild.wumpa_bank, 5000) # 10000 - 5000

    def test_upgrade_armory(self):
        # Mock session
        session = MagicMock()
        patcher = patch.object(self.guild_service.db, 'get_session', return_value=session)
        patcher.start()
        self.addCleanup(patcher.stop)
        
        # Mock leader member
        member = GuildMember(guild_id=1, user_id=111, role="Leader")
        
        # Mock guild with funds (armeria lv0→1 costa 10000)
        guild = Guild(id=1, name="TestGuild", armory_level=0, wumpa_bank=10000)
        
        def query_side_effect(*args, **kwargs):
            model = args[0] if args else None
            query = MagicMock()
            if model == GuildMember:
                query.filter_by.return_value.first.return_value = member
            elif model == Guild:
                query.filter_by.return_value.first.return_value = guild
            return query
            
        session.query.side_effect = query_side_effect
        
        # Test upgrade armory (lv0→1 = 10000 wumpa)
        success, msg = self.guild_service.upgrade_armory(leader_id=111)
        self.assertTrue(success, f"Upgrade failed with message: {msg}")
        self.assertEqual(guild.armory_level, 1)
        self.assertEqual(guild.wumpa_bank, 0) # 10000 - 10000

    def test_expand_village(self):
        # Mock session
        session = MagicMock()
        patcher = patch.object(self.guild_service.db, 'get_session', return_value=session)
        patcher.start()
        self.addCleanup(patcher.stop)
        
        # Mock leader member
        member = GuildMember(guild_id=1, user_id=111, role="Leader")
        
        # Mock guild with funds (villaggio lv1→2 costa 20000)
        guild = Guild(id=1, name="TestGuild", village_level=1, member_limit=5, wumpa_bank=50000)
        
        def query_side_effect(*args, **kwargs):
            model = args[0] if args else None
            query = MagicMock()
            if model == GuildMember:
                query.filter_by.return_value.first.return_value = member
            elif model == Guild:
                query.filter_by.return_value.first.return_value = guild
            return query
            
        session.query.side_effect = query_side_effect
        
        # Test expand village (lv1→2 = 20000 wumpa)
        success, msg = self.guild_service.expand_village(leader_id=111)
        self.assertTrue(success, f"Upgrade failed with message: {msg}")
        self.assertEqual(guild.village_level, 2)
        self.assertEqual(guild.member_limit, 10) # 5 + 5
        self.assertEqual(guild.wumpa_bank, 30000) # 50000 - 20000

if __name__ == '__main__':
    unittest.main()
