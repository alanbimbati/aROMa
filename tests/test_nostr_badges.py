import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scripts.generate_badge_images import definitions, OUT_DIR, TIER_COLORS
from services.nostr_service import badge_image_name


class TestBadgeParity(unittest.TestCase):
    def test_every_achievement_tier_has_a_badge_image(self):
        missing = []
        for key, _name, tiers in definitions():
            for tier in tiers:
                self.assertIn(tier, TIER_COLORS, f"{key}: tier '{tier}' has no badge colour")
                if not os.path.exists(os.path.join(OUT_DIR, f"{badge_image_name(key, tier)}.png")):
                    missing.append(f"{key}-{tier}")
        self.assertEqual(missing, [], "run scripts/generate_badge_images.py")

    def test_podium_badges_share_three_images(self):
        for place in (1, 2, 3):
            name = badge_image_name(f"season_7_podium_{place}", "gold")
            self.assertEqual(name, f"season-podium-{place}")
            self.assertTrue(os.path.exists(os.path.join(OUT_DIR, f"{name}.png")))


if __name__ == '__main__':
    unittest.main()
