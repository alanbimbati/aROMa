import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scripts import marvel_roster as roster

SUPPORTED_STATUS = {'burn', 'poison', 'stun', 'confusion', 'mind_control', 'freeze', 'bleed', 'slow', 'weakness',
                    'defense_up', 'buff_attack', 'buff_defense'}


class TestMarvelRoster(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.rows, cls.abilities = roster.regenerate()
        cls.marvel = [r for r in cls.rows if r['character_group'] == 'Marvel']
        cls.by_id = {r['id']: r for r in cls.rows}

    def test_ids_and_names_are_unique(self):
        ids = [r['id'] for r in self.rows]
        self.assertEqual(len(ids), len(set(ids)))
        names = [r['nome'] for r in self.marvel]
        self.assertEqual(len(names), len(set(names)))

    def test_levels_are_spread_over_the_whole_range(self):
        per_decile = [0] * 10
        for r in self.marvel:
            per_decile[(int(r['livello']) - 1) // 10] += 1
        self.assertTrue(all(9 <= n for n in per_decile), per_decile)
        # the first tier holds the starter heroes; from there on no decile may be far from another
        self.assertLessEqual(max(per_decile[1:]) - min(per_decile[1:]), 5, per_decile)

    def test_every_tier_of_access_is_present_across_levels(self):
        tiers = {}
        for r in self.marvel:
            tiers.setdefault((int(r['livello']) - 1) // 10, set()).add(int(r['lv_premium']))
        for decile in range(0, 9):
            self.assertIn(0, tiers[decile], f"no free character in decile {decile}")
        for decile in range(2, 10):
            self.assertIn(1, tiers[decile], f"no premium character in decile {decile}")

    def test_stats_follow_the_level_curve_within_the_archetype_limits(self):
        for r in self.rows:
            if r['character_group'] != 'Marvel' or int(r['id']) < roster.FIRST_NEW_ID:
                continue
            level = int(r['livello'])
            base = 20 + 6 * level
            self.assertLessEqual(abs(int(r['special_attack_damage']) - base), base * 0.08, r['nome'])
            self.assertEqual(int(r['exp_required']), 50 * level * level, r['nome'])

    def test_archetypes_are_balanced_against_each_other(self):
        for arch in roster.ARCHETYPES:
            for level in range(10, 101, 10):
                ev = roster.expected_damage(level, arch) / roster.expected_damage(level, 'balanced')
                mana = roster.stats(level, arch)['mana'] / roster.stats(level, 'balanced')['mana']
                self.assertTrue(0.90 <= ev <= 1.06, (arch, level, ev))
                self.assertTrue(0.90 <= mana <= 1.07, (arch, level, mana))
                self.assertLessEqual(abs(roster.stats(level, arch)['speed'] - roster.stats(level, 'balanced')['speed']), 6)

    def test_prices_match_how_a_character_is_obtained(self):
        for r in self.marvel:
            tier, price = int(r['lv_premium']), int(r['price'])
            if tier == roster.SHOP:
                self.assertGreater(price, 0, r['nome'])
            else:
                self.assertEqual(price, 0, r['nome'])  # a priced free/premium card would be sold but unusable

    def test_every_character_has_one_holder_except_the_shared_starter(self):
        for r in self.marvel:
            expected = '-1' if r['nome'] == 'Stan Lee' else '1'
            self.assertEqual(r['max_concurrent_owners'], expected, r['nome'])

    def test_the_starting_hero_is_free(self):
        stan = next(r for r in self.marvel if r['nome'] == 'Stan Lee')
        self.assertEqual(int(stan['lv_premium']), roster.FREE)

    def test_forms_hang_from_a_weaker_base(self):
        for r in self.marvel:
            if r['is_transformation'] == '1':
                base = self.by_id[str(r['base_character_id'])]
                self.assertLess(int(base['livello']), int(r['livello']), r['nome'])
                self.assertEqual(str(r['required_character_id']), str(r['base_character_id']))

    def test_every_marvel_character_has_one_supported_ability(self):
        self.assertEqual({a['character_id'] for a in self.abilities}, {r['id'] for r in self.marvel})
        self.assertEqual(len(self.abilities), len(self.marvel))
        for a in self.abilities:
            self.assertIn(a['status_effect'], SUPPORTED_STATUS)
            self.assertGreater(int(a['status_chance']), 0)

    def test_season_pass_covers_every_rank_on_both_tracks(self):
        rewards = roster.pass_rewards(self.rows)
        for track in (0, 1):
            ranks = {r['level_required'] for r in rewards if r['is_premium'] == track and r['reward_type'] == 'points'}
            self.assertEqual(ranks, set(range(1, roster.PASS_RANKS + 1)))
        premium = sum(r['reward_value'] for r in rewards if r['is_premium'] and r['reward_type'] == 'points')
        free = sum(r['reward_value'] for r in rewards if not r['is_premium'] and r['reward_type'] == 'points')
        self.assertGreater(premium, free)
        for r in rewards:
            if r['reward_type'] == 'character':
                self.assertIn(str(r['reward_value']), self.by_id)
                self.assertEqual(int(self.by_id[str(r['reward_value'])]['lv_premium']), roster.SHOP,
                                 f"{r['reward_name']} should be a shop character, premium ones come with the pass anyway")


if __name__ == '__main__':
    unittest.main()
