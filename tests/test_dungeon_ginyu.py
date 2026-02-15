import pytest
from unittest.mock import MagicMock, patch
from services.dungeon_service import DungeonService
from models.dungeon import Dungeon
import json

class TestGinyuDungeon:
    
    @pytest.fixture
    def dungeon_service(self):
        return DungeonService()

    def test_ginyu_dungeon_structure(self, dungeon_service):
        """Verify Dungeon 21 has exactly 2 steps now"""
        dungeon_def = dungeon_service.get_dungeon_def(21)
        assert dungeon_def is not None, "Dungeon 21 not found"
        assert dungeon_def['name'] == "Squadra Ginyu (Saga)"
        
        steps = dungeon_def['steps']
        assert isinstance(steps, list), "Steps should be a list"
        assert len(steps) == 2, f"Expected 2 steps, found {len(steps)}"
        
        # Step 1: Team Fight
        step1 = steps[0]
        assert 'mobs' in step1
        assert len(step1['mobs']) == 4
        assert step1['boss'] == "Capitano Ginyu"
        
        mob_names = [m['name'] for m in step1['mobs']]
        assert "Guldo" in mob_names
        assert "Recoome" in mob_names
        assert "Burter" in mob_names
        assert "Jeice" in mob_names
        
        # Step 2: Final Boss
        step2 = steps[1]
        assert 'boss' in step2
        assert step2['boss'] == "Ginyu (Goku Body)"

    @patch('services.pve_service.PvEService.spawn_specific_mob')
    @patch('services.pve_service.PvEService.spawn_boss')
    def test_ginyu_spawn_logic(self, mock_spawn_boss, mock_spawn_mob, dungeon_service):
        """Verify that spawning logic actually calls spawn for all members"""
        # Mock DB session
        mock_session = MagicMock()
        
        # Mock Dungeon object
        mock_dungeon = MagicMock()
        mock_dungeon.id = 999
        mock_dungeon.chat_id = 12345
        mock_dungeon.dungeon_def_id = 21
        
        # Setup mocks to return success
        mock_spawn_mob.return_value = (True, "Mob Spawned", 101)
        mock_spawn_boss.return_value = (True, "Boss Spawned", 102)
        
        # Mock session.query
        mock_session.query.return_value.filter_by.return_value.first.return_value = mock_dungeon
        
        # Test Step 1 Spawn
        events, mob_ids = dungeon_service.spawn_step(999, 1, session=mock_session)
        
        # Verify calls
        # 4 Mobs + 1 Boss = 5 calls total
        assert mock_spawn_mob.call_count == 4
        assert mock_spawn_boss.call_count == 1
        
        # Verify specific mobs were requested
        # spawn_specific_mob(mob_name=None, chat_id=None, ...)
        spawned_names = []
        for call in mock_spawn_mob.call_args_list:
            args, kwargs = call
            # mob_name is passed as keyword arg
            if 'mob_name' in kwargs:
                spawned_names.append(kwargs['mob_name'])
                
        assert "Guldo" in spawned_names
        assert "Recoome" in spawned_names
        assert "Burter" in spawned_names
        assert "Jeice" in spawned_names
        
        # Verify Boss
        boss_call = mock_spawn_boss.call_args
        boss_args, boss_kwargs = boss_call
        boss_name = boss_kwargs.get('boss_name')
        assert boss_name == "Capitano Ginyu"

    @patch('services.pve_service.PvEService.spawn_boss')
    def test_ginyu_step_2_spawn(self, mock_spawn_boss, dungeon_service):
        """Verify Step 2 spawns Ginyu Goku"""
        mock_session = MagicMock()
        mock_dungeon = MagicMock()
        mock_dungeon.id = 999
        mock_dungeon.chat_id = 12345
        mock_dungeon.dungeon_def_id = 21
        
        mock_session.query.return_value.filter_by.return_value.first.return_value = mock_dungeon
        mock_spawn_boss.return_value = (True, "Boss Spawned", 103)
        
        events, mob_ids = dungeon_service.spawn_step(999, 2, session=mock_session)
        
        boss_args, boss_kwargs = mock_spawn_boss.call_args
        boss_name = boss_kwargs.get('boss_name') if 'boss_name' in boss_kwargs else boss_args[0]
        assert boss_name == "Ginyu (Goku Body)"
