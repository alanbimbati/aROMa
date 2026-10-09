import csv
import json
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scripts.marvel_dungeons import KEPT, LADDER, build_dungeons, dungeon_ids
from scripts import marvel_achievements

DATA = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'data')


def _csv(name):
    with open(os.path.join(DATA, name), newline='', encoding='utf-8') as f:
        return list(csv.DictReader(f, skipinitialspace=True))


class TestMarvelDungeons(unittest.TestCase):
    def test_ladder_climbs_in_difficulty_and_reward(self):
        rows = build_dungeons()
        difficulties = [r['difficulty'] for r in rows]
        self.assertEqual(difficulties, sorted(difficulties), "unlocking follows the id order: it must get harder")
        self.assertEqual(min(difficulties), 1, "a freshly reset player needs somewhere to start")
        self.assertEqual(max(difficulties), 10)
        wumpa = [r['rewards']['wumpa'] for r in rows]
        self.assertEqual(wumpa, sorted(wumpa))
        self.assertEqual([r['id'] for r in rows], list(range(13, 13 + len(rows))))

    def test_every_step_names_a_mob_or_boss_that_exists(self):
        mobs = {r['nome'] for r in _csv('mobs.csv')}
        bosses = {r['nome'] for r in _csv('bosses.csv')}
        for row in build_dungeons():
            for step in row['steps']:
                for mob in step.get('mobs', []):
                    self.assertIn(mob['name'], mobs, row['name'])
                if 'boss' in step:
                    self.assertIn(step['boss'], bosses, row['name'])

    def test_the_files_match_the_ladder(self):
        on_disk = {r['name']: int(r['id']) for r in _csv('dungeons.csv') if r['saga'] == 'Marvel'}
        self.assertEqual(on_disk, dungeon_ids(), "run scripts/marvel_dungeons.py --apply")

    def test_a_dungeon_ends_on_a_boss_and_its_tier_fits(self):
        bosses = {r['nome']: int(r['difficulty']) for r in _csv('bosses.csv') if r['saga'] == 'Marvel'}
        for row in build_dungeons():
            last = row['steps'][-1]
            self.assertIn('boss', last, row['name'])
            self.assertLessEqual(abs(bosses[last['boss']] - row['difficulty']), 3, row['name'])

    def test_dungeon_achievements_point_at_real_dungeons(self):
        ids = set(dungeon_ids().values())
        for row in marvel_achievements.build():
            stat = row[3]
            if stat.startswith('dungeon_def_'):
                self.assertIn(int(stat.split('_')[2]), ids, row[0])
        on_disk = {r['key']: r['stat_key'] for r in _csv('season2_marvel_achievements.csv')}
        self.assertEqual(on_disk, {row[0]: row[3] for row in marvel_achievements.build()},
                         "run python -m scripts.marvel_achievements")

    def test_kept_dungeons_keep_their_steps(self):
        by_name = {r['name']: r for r in build_dungeons()}
        for name in KEPT:
            self.assertIn(name, by_name)
        self.assertEqual(len([d for d in LADDER if d['name'] in KEPT]), len(KEPT))


if __name__ == '__main__':
    unittest.main()


def test_recommended_level_sets_enemy_levels_and_a_smooth_budget():
    from services.dungeon_service import DungeonService
    from services.pve_service import PvEService
    d = {'recommended_level': 16, 'steps': [{'mobs': [{'name': 'x', 'count': 3}]}, {'boss': 'y'}]}
    assert DungeonService.stage_levels(d, 1) == (16, 18)
    assert DungeonService.stage_levels(d, 2) == (18, 20)
    assert DungeonService.stage_levels({'steps': []}, 1) == (None, None)  # Dragon Ball keeps its random levels
    hp, dmg = zip(*(PvEService.level_budget(lv) for lv in (1, 30, 60, 96)))
    assert list(hp) == sorted(hp) and list(dmg) == sorted(dmg)
    assert PvEService.level_budget(10, boss=True)[0] > PvEService.level_budget(10)[0]
    assert PvEService.level_budget(10, weight=0.25)[0] < PvEService.level_budget(10)[0]
    assert DungeonService.enemy_weight({'steps': [{'boss': 'a'}]}) == 1.0


def test_dungeon_rewards_follow_the_level_and_favour_teams():
    from services import dungeon_rewards as dr
    exp, wumpa = dr.budget(5)
    assert exp < 10 * (6 ** 2.5 - 5 ** 2.5)          # less than a level of EXP for the first dungeon, solo
    assert wumpa < 200                                 # and a modest purse
    levels = [5, 9, 14, 35, 100]
    assert [dr.budget(l)[0] for l in levels] == sorted(dr.budget(l)[0] for l in levels)
    solo = dr.completion(5)
    team = dr.completion(5, 4)
    assert team[0] > solo[0] and team[1] > solo[1]     # everyone earns more in a team...
    assert dr.team_bonus(50) == 2.0                    # ...up to double
    # a team of four splitting one kill by damage: each still gets more than a lone player would
    kill_solo = dr.kill_pool(5, 9, False, 1)
    kill_team = dr.kill_pool(5, 9, False, 4)
    assert kill_team[0] / 4 > kill_solo[0] and kill_team[1] / 4 > kill_solo[1]
    # the whole dungeon, kills plus completion, stays near the budget for a lone player
    d = {'steps': [{'mobs': [{'name': 'x', 'count': 5}]}, {'boss': 'y'}]}
    from services.dungeon_service import DungeonService
    units = DungeonService.enemy_units(d)
    total = sum(dr.kill_pool(5, units, False)[0] for _ in range(5)) + dr.kill_pool(5, units, True)[0] + dr.completion(5)[0]
    assert abs(total - exp) <= 8
