import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from webapp import games, games_clean as gc


class TestCleaning(unittest.TestCase):
    def test_platform_spellings_collapse(self):
        for raw in ('DS', 'NDS', 'Nintendo DS'):
            self.assertEqual(gc.platforms(raw), ['Nintendo DS'])
        for raw in ('GBA', 'GameBoyAdvance', 'Game Boy Advance (GBA)'):
            self.assertEqual(gc.platforms(raw), ['Game Boy Advance'])
        self.assertEqual(gc.platforms('PC, DOS'), ['PC', 'PC (DOS)'])
        self.assertEqual(gc.platforms('#3ds #Cia'), ['Nintendo 3DS'])

    def test_genre_notes_and_hashtags_are_not_genres(self):
        self.assertEqual(gc.genres('Avventura (punta e clicca)'), ['Avventura'])
        self.assertEqual(gc.genres('Azione, avventura'), ['Azione', 'Avventura'])
        self.assertEqual(gc.genres('#azione #picchiaduro'), ['Azione', 'Picchiaduro'])
        self.assertEqual(gc.genres('horror'), ['Horror'])

    def test_language_region_year(self):
        self.assertEqual(gc.languages('Multilingue (incluso Italiano)'), (['Italiano'], True))
        self.assertEqual(gc.languages('Multilingue'), ([], True))  # says nothing about Italian: not guessed
        self.assertEqual(sorted(gc.languages('Inglese, italiano')[0]), ['Inglese', 'Italiano'])
        self.assertEqual(gc.regions('USA (con patch in italiano)'), ['USA'])
        self.assertEqual(gc.regions('Globale'), ['Internazionale'])
        self.assertIsNone(gc.year('1850'))
        self.assertIsNone(gc.year(''))
        self.assertEqual(gc.year('1998'), 1998)

    def test_arcade_is_a_genre_not_a_platform(self):
        both = gc.clean_row(dict(id='1', title='Break Out', platform='PS1, Arcade', genre='Sport'))
        self.assertEqual((both['platforms'], both['genres']), (['PS1'], ['Sport', 'Arcade']))
        only = gc.clean_row(dict(id='2', title='Asteroids', platform='Arcade', genre='Sparatutto'))
        self.assertEqual((only['platforms'], only['genres']), (['Altro'], ['Sparatutto', 'Arcade']))
        self.assertEqual(gc.clean_row(dict(id='3', title='x', platform='MAME (Multiple Arcade Machine Emulator)'))['platforms'], ['Altro'])

    def test_developer_and_publisher_come_from_the_text(self):
        self.assertEqual(gc.credits('MotoGP 15 è un videogioco sviluppato da Milestone S.r.l. e pubblicato da Namco Bandai Games per PC nel 2015.'),
                         ('Milestone', 'Bandai Namco'))
        self.assertEqual(gc.credits('Tekken è un gioco sviluppato e pubblicato da Namco nel 1995.'), ('Namco', 'Namco'))
        self.assertEqual(gc.credits('Gioco di volo e sparatutto ambientato in un futuro distopico.'), ('', ''))  # not invented
        self.assertEqual(gc.clean_row(dict(id='1', title='x', description='Un #gioco   bello'))['description'], 'Un gioco bello')

    def test_duplicates_merge_keeping_the_complete_row(self):
        rows = [dict(id='1', title='Crash  Bandicoot', platform='PS1', genre='', description='', language='', year='', region=''),
                dict(id='2', title='crash bandicoot', platform='PSX', genre='Piattaforma', description='x', language='', year='1996', region='Europa')]
        games_list, report = gc.clean(rows)
        self.assertEqual(len(games_list), 1)
        self.assertEqual(games_list[0]['year'], 1996)
        self.assertEqual(report['duplicates_merged'], 1)


@unittest.skipUnless(games.load(), 'catalogue not built')
class TestSearch(unittest.TestCase):
    def test_accents_and_terms(self):
        self.assertEqual(games.fold('Pokémon'), 'pokemon')
        r = games.search(q='crash')
        self.assertTrue(r['total'] and all('crash' in g['title'].lower() or 'crash' in g['description'].lower() for g in r['items']))

    def test_filters_and_facets_agree(self):
        r = games.search(platform='PS1', genre='Horror')
        self.assertTrue(all('PS1' in g['platforms'] and 'Horror' in g['genres'] for g in r['items']))
        # every facet value found inside the result really narrows to a non-empty list
        for name, _ in r['facets']['platforms'][:3]:
            self.assertGreater(games.search(platform=name, genre='Horror')['total'], 0)

    def test_sort_by_year_puts_unknown_last_and_paginates(self):
        a = games.search(sort='anno', per_page=10)
        years = [g['year'] for g in a['items']]
        self.assertEqual(years, sorted(years, reverse=True))
        self.assertEqual(len(games.search(per_page=7)['items']), 7)
        self.assertEqual(games.search(per_page=7, page=2)['page'], 2)

    def test_no_message_links_or_owners_in_what_is_served(self):
        item = games.search(per_page=1)['items'][0]
        self.assertFalse({'message_link', 'preso_da', 'link'} & set(item))
