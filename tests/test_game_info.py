import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services import game_info


def game(**kw):
    base = dict(id=7, title='Tom & Jerry <3', platforms=['PS1'], year=1999, genres=['Azione'], languages=['Italiano'],
                multilanguage=False, regions=['Europa'], developer='Capcom', publisher='Capcom', description='Un gioco.')
    base.update(kw)
    return base


class TestGameInfo(unittest.TestCase):
    def test_start_payload(self):
        self.assertEqual(game_info.parse_start_payload('/start game_123'), 123)
        self.assertEqual(game_info.parse_start_payload('/start@AromaBot game_5'), 5)
        for bad in ('/start', '/start game_', '/start game_abc', '/start other_1', None, '/start game_1; drop'):
            self.assertIsNone(game_info.parse_start_payload(bad), bad)

    def test_card_is_escaped_and_fits_a_caption(self):
        text = game_info.card_text(game())
        self.assertIn('Tom &amp; Jerry &lt;3', text)
        self.assertIn('Capcom', text)
        self.assertLessEqual(len(game_info.card_text(game(description='x' * 5000))), game_info.CAPTION_LIMIT)
        long = game_info.card_text(game(description='<&>' * 600))
        self.assertLessEqual(len(long), game_info.CAPTION_LIMIT)
        self.assertNotIn('<&>', long)

    def test_card_has_no_file_or_link_to_one(self):
        text = game_info.card_text(game())
        self.assertNotIn('t.me', text)
        self.assertNotIn('http', text)


if __name__ == '__main__':
    unittest.main()
