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
        """Dungeon 4 has four steps: two pairs of Ginyu Force members, then the two bosses"""
        dungeon_def = dungeon_service.get_dungeon_def(4)
        assert dungeon_def is not None, "Dungeon 4 not found"
        assert dungeon_def['name'] == "Squadra Ginyu"

        steps = dungeon_def['steps']
        assert isinstance(steps, list), "Steps should be a list"
        assert len(steps) == 4, f"Expected 4 steps, found {len(steps)}"

        assert [m['name'] for m in steps[0]['mobs']] == ["Guldo", "Recoome"]
        assert [m['name'] for m in steps[1]['mobs']] == ["Burter", "Jeice"]
        assert steps[2]['boss'] == "Capitano Ginyu"
        assert steps[3]['boss'] == "Ginyu (Goku Body)"

    @patch('services.pve_service.PvEService.apply_pending_effects', return_value=[])
    @patch('services.pve_service.PvEService.spawn_specific_mob')
    @patch('services.dungeon_service.DungeonService._assign_mob_to_dungeon')
    def test_ginyu_spawn_logic(self, mock_assign, mock_spawn_mob, mock_pending, dungeon_service):
        """Steps 1 and 2 spawn their two named mobs each"""
        mock_session = MagicMock()
        mock_dungeon = MagicMock()
        mock_dungeon.id = 999
        mock_dungeon.chat_id = 12345
        mock_dungeon.dungeon_def_id = 4
        mock_spawn_mob.return_value = (True, "Mob Spawned", 101)
        mock_session.query.return_value.filter_by.return_value.first.return_value = mock_dungeon

        for step, expected in ((1, ["Guldo", "Recoome"]), (2, ["Burter", "Jeice"])):
            mock_spawn_mob.reset_mock()
            events, mob_ids = dungeon_service.spawn_step(999, step, session=mock_session)
            spawned = [call.kwargs['mob_name'] for call in mock_spawn_mob.call_args_list]
            assert spawned == expected
            assert len(mob_ids) == 2

    @patch('services.pve_service.PvEService.spawn_boss')
    def test_ginyu_boss_steps(self, mock_spawn_boss, dungeon_service):
        """Step 3 spawns Capitano Ginyu, step 4 Ginyu in Goku's body"""
        mock_session = MagicMock()
        mock_dungeon = MagicMock()
        mock_dungeon.id = 999
        mock_dungeon.chat_id = 12345
        mock_dungeon.dungeon_def_id = 4
        mock_session.query.return_value.filter_by.return_value.first.return_value = mock_dungeon
        mock_spawn_boss.return_value = (True, "Boss Spawned", 103)

        for step, expected in ((3, "Capitano Ginyu"), (4, "Ginyu (Goku Body)")):
            dungeon_service.spawn_step(999, step, session=mock_session)
            boss_args, boss_kwargs = mock_spawn_boss.call_args
            boss_name = boss_kwargs.get('boss_name') if 'boss_name' in boss_kwargs else boss_args[0]
            assert boss_name == expected
