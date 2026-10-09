import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from fastapi.testclient import TestClient
except Exception as e:  # the test client needs its HTTP library installed (see requirements.dev.txt)
    raise unittest.SkipTest(f"fastapi test client unavailable: {e}")

from database import Database
from models.nostr import NostrBadgeOutbox, NostrLinkChallenge
from models.character_ownership import CharacterOwnership
from models.user import Utente
from services.character_loader import get_character_loader
from models.webapp import WebLoginToken
from webapp import auth
from webapp.app import app

USER_ID = 880011
DEAD = 'http://127.0.0.1:1/none'  # a tunnel that is not there, whatever the machine's DNS resolves
os.environ['WEBAPP_URL'] = 'https://aroma.example.org'  # login links need a public address
SAME_SITE = {'X-Requested-With': 'aroma'}


class TestWebApp(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app, follow_redirects=False)
        cls.client.__enter__()  # runs the startup hook (creates the login table)
        session = Database().get_session()
        session.query(WebLoginToken).filter_by(user_id=USER_ID).delete()
        session.query(NostrLinkChallenge).filter_by(user_id=USER_ID).delete()
        session.query(NostrBadgeOutbox).filter_by(user_id=USER_ID).delete()
        session.query(Utente).filter_by(id_telegram=USER_ID).delete()
        session.add(Utente(id_telegram=USER_ID, username='webtest', nome='Web Test', exp=0, points=5, livello=1,
                           premium=0, livello_selezionato=1))
        session.commit()
        session.close()

    @classmethod
    def tearDownClass(cls):
        cls.client.__exit__(None, None, None)

    def anonymous(self):
        return TestClient(app, follow_redirects=False)

    def logged_in(self):
        client = TestClient(app, follow_redirects=False)
        client.cookies.set(auth.COOKIE, auth.make_session(USER_ID))
        return client

    # --- public ---
    def test_catalogue_is_public_and_complete(self):
        r = self.client.get('/api/characters')
        self.assertEqual(r.status_code, 200)
        chars = r.json()
        self.assertGreater(len(chars), 400)
        self.assertTrue({'id', 'name', 'level', 'tier', 'attack', 'img'} <= set(chars[0]))
        self.assertEqual({c['tier'] for c in chars}, {'free', 'shop', 'premium'})

    def test_character_sheet_and_unknown_character(self):
        chars = self.client.get('/api/characters').json()
        detail = self.client.get(f"/api/characters/{chars[0]['id']}")
        self.assertEqual(detail.status_code, 200)
        self.assertIn('family', detail.json())
        self.assertEqual(self.client.get('/api/characters/99999999').status_code, 404)

    def test_pictures_only_in_the_known_widths(self):
        self.assertEqual(self.client.get('/img/stan_lee/300.webp').status_code, 404)
        self.assertEqual(self.client.get('/img/..%2F..%2Fetc%2Fpasswd/256.webp').status_code, 404)

    def test_badge_names_cannot_escape_the_folder(self):
        self.assertEqual(self.client.get('/badges/..%2F..%2Fsettings.py').status_code, 404)
        self.assertEqual(self.client.get('/badges/not-a-badge.png').status_code, 404)

    def test_share_page_has_the_preview_tags(self):
        char = self.client.get('/api/characters').json()[0]
        page = self.client.get(f"/p/{char['id']}")
        self.assertEqual(page.status_code, 200)
        self.assertIn('og:title', page.text)
        self.assertEqual(self.client.get('/p/99999999').status_code, 404)

    # --- who holds a character ---
    def test_a_form_in_use_makes_the_whole_family_taken_and_names_who(self):
        loader = get_character_loader()
        form = loader.get_character_by_name('Spider-Man')            # a form of Peter Parker
        family = set(loader.get_character_family_ids(form['id']))
        self.assertGreater(len(family), 1)
        other_id = USER_ID + 1
        session = Database().get_session()
        session.query(CharacterOwnership).filter(CharacterOwnership.user_id.in_([USER_ID, other_id])).delete()
        session.query(Utente).filter_by(id_telegram=other_id).delete()
        session.add(Utente(id_telegram=other_id, username='holder', nome='Holder', game_name='Il Ragno', exp=0, points=0, livello=1, premium=0))
        session.add(CharacterOwnership(user_id=other_id, character_id=form['id']))
        session.commit()
        session.close()
        try:
            taken = self.logged_in().get('/api/me/characters').json()['taken']
            self.assertTrue({str(i) for i in family} <= set(taken), "every form of the family is taken")
            self.assertEqual(taken[str(form['id'])]['by'], 'Il Ragno')
            self.assertEqual(taken[str(form['id'])]['form'], 'Spider-Man')
            self.assertFalse(taken[str(form['id'])]['mine'])
            mine = TestClient(app)
            mine.cookies.set(auth.COOKIE, auth.make_session(other_id))
            self.assertTrue(mine.get('/api/me/characters').json()['taken'][str(form['id'])]['mine'])
            selectable = self.logged_in().get('/api/me/characters').json()['selectable']
            self.assertFalse(family & set(selectable), "nobody else can pick any of them")
        finally:
            session = Database().get_session()
            session.query(CharacterOwnership).filter_by(user_id=other_id).delete()
            session.query(Utente).filter_by(id_telegram=other_id).delete()
            session.commit()
            session.close()

    def test_the_shared_starter_is_never_shown_as_taken(self):
        stan = get_character_loader().get_character_by_name('Stan Lee')
        session = Database().get_session()
        session.query(CharacterOwnership).filter_by(user_id=USER_ID).delete()
        session.add(CharacterOwnership(user_id=USER_ID, character_id=stan['id']))
        session.commit()
        session.close()
        try:
            self.assertNotIn(str(stan['id']), self.logged_in().get('/api/me/characters').json()['taken'])
        finally:
            session = Database().get_session()
            session.query(CharacterOwnership).filter_by(user_id=USER_ID).delete()
            session.commit()
            session.close()

    # --- private ---
    def test_private_endpoints_need_a_session(self):
        client = self.anonymous()
        for path in ('/api/me', '/api/me/stats', '/api/me/achievements', '/api/season', '/api/dungeons', '/api/me/nostr'):
            self.assertEqual(client.get(path).status_code, 401, path)

    def test_games_api_tells_the_page_which_bot_to_open(self):
        client = self.logged_in()
        saved = os.environ.get('BOT_USERNAME')
        try:
            os.environ['BOT_USERNAME'] = '@AromaBot'
            self.assertEqual(client.get('/api/games', params={'per_page': 1}).json()['bot'], 'AromaBot')
            os.environ['BOT_USERNAME'] = ''
            self.assertEqual(client.get('/api/games', params={'per_page': 1}).json()['bot'], '')
        finally:
            if saved is None:
                os.environ.pop('BOT_USERNAME', None)
            else:
                os.environ['BOT_USERNAME'] = saved

    def test_game_covers_need_login_and_are_flagged(self):
        import tempfile
        from webapp import app as webapp_app, games
        from PIL import Image
        with tempfile.TemporaryDirectory() as tmp:
            Image.new('RGB', (8, 8)).save(os.path.join(tmp, '5.webp'), 'WEBP')
            saved = webapp_app.GAME_COVERS, games.COVERS
            webapp_app.GAME_COVERS = games.COVERS = tmp
            try:
                self.assertEqual(self.anonymous().get('/img/game/5.webp').status_code, 401)
                client = self.logged_in()
                r = client.get('/img/game/5.webp')
                self.assertEqual((r.status_code, r.headers['content-type']), (200, 'image/webp'))
                self.assertEqual(client.get('/img/game/6.webp').status_code, 404)
                self.assertEqual(client.get('/api/games/5').json()['cover'], True)
                self.assertEqual(client.get('/api/games/6').json()['cover'], False)
            finally:
                webapp_app.GAME_COVERS, games.COVERS = saved

    def test_login_link_works_once_and_gives_a_session(self):
        link = auth.create_login_link(USER_ID)
        token = link.split('token=')[1]
        client = self.anonymous()
        first = client.get(f'/login?token={token}')
        self.assertEqual(first.status_code, 303)
        self.assertIn(auth.COOKIE, first.headers.get('set-cookie', ''))
        again = self.anonymous().get(f'/login?token={token}')
        self.assertIn('expired', again.headers['location'])
        self.assertEqual(self.anonymous().get('/login?token=garbage').status_code, 307)

    def test_login_link_never_points_at_localhost(self):
        saved = os.environ.get('WEBAPP_URL'), auth.NGROK_API, auth.QUICKTUNNEL_API
        auth.NGROK_API = auth.QUICKTUNNEL_API = DEAD
        auth._ngrok_cache.update(at=0.0, url=None)
        try:
            for bad in ('', 'http://localhost:8080', 'http://127.0.0.1:8080', 'http://0.0.0.0:8080', 'aroma.example.org'):
                os.environ['WEBAPP_URL'] = bad
                with self.assertRaises(RuntimeError, msg=bad):
                    auth.create_login_link(USER_ID)
            os.environ.pop('WEBAPP_URL')
            with self.assertRaises(RuntimeError):
                auth.create_login_link(USER_ID)
            os.environ['WEBAPP_URL'] = 'https://aroma.example.org/'
            self.assertTrue(auth.create_login_link(USER_ID).startswith('https://aroma.example.org/login?token='))
        finally:
            os.environ['WEBAPP_URL'], auth.NGROK_API, auth.QUICKTUNNEL_API = saved
            auth._ngrok_cache.update(at=0.0, url=None)

    def test_public_address_comes_from_ngrok_when_not_configured(self):
        import json
        import threading
        from http.server import BaseHTTPRequestHandler, HTTPServer

        class Fake(BaseHTTPRequestHandler):
            def do_GET(self):
                body = json.dumps({'tunnels': [{'public_url': 'http://x.ngrok.io'}, {'public_url': 'https://abc.ngrok-free.app'}]}).encode()
                self.send_response(200)
                self.end_headers()
                self.wfile.write(body)

            def log_message(self, *a):
                pass

        server = HTTPServer(('127.0.0.1', 0), Fake)
        threading.Thread(target=server.serve_forever, daemon=True).start()
        saved = os.environ.get('WEBAPP_URL'), auth.NGROK_API, auth.QUICKTUNNEL_API
        try:
            os.environ['WEBAPP_URL'] = ''
            auth.QUICKTUNNEL_API = DEAD
            auth.NGROK_API = f'http://127.0.0.1:{server.server_port}/api/tunnels'
            auth._ngrok_cache.update(at=0.0, url=None)
            self.assertEqual(auth.webapp_url(), 'https://abc.ngrok-free.app')  # the https one
            self.assertTrue(auth.create_login_link(USER_ID).startswith('https://abc.ngrok-free.app/login?token='))
            os.environ['WEBAPP_URL'] = 'https://fixed.example.org'  # an explicit address wins
            self.assertEqual(auth.webapp_url(), 'https://fixed.example.org')
            server.shutdown()
            os.environ['WEBAPP_URL'] = ''
            auth._ngrok_cache.update(at=0.0, url=None)  # tunnel gone: no link rather than a stale one
            with self.assertRaises(RuntimeError):
                auth.webapp_url()
        finally:
            os.environ['WEBAPP_URL'], auth.NGROK_API, auth.QUICKTUNNEL_API = saved
            auth._ngrok_cache.update(at=0.0, url=None)

    def test_a_new_link_cancels_the_previous_one(self):
        old = auth.create_login_link(USER_ID).split('token=')[1]
        auth.create_login_link(USER_ID)
        self.assertIn('expired', self.anonymous().get(f'/login?token={old}').headers['location'])

    def test_a_tampered_cookie_is_not_a_session(self):
        client = TestClient(app)
        client.cookies.set(auth.COOKIE, auth.make_session(USER_ID) + 'x')
        self.assertEqual(client.get('/api/me').status_code, 401)

    def test_profile_and_the_pages_that_read_it(self):
        client = self.logged_in()
        me = client.get('/api/me')
        self.assertEqual(me.status_code, 200)
        self.assertEqual(me.json()['id'], USER_ID)
        for path in ('/api/me/characters', '/api/me/stats', '/api/me/achievements', '/api/season', '/api/dungeons', '/api/me/nostr'):
            self.assertEqual(client.get(path).status_code, 200, path)

    def test_state_changing_calls_must_come_from_the_app(self):
        client = self.logged_in()
        self.assertEqual(client.post('/api/me/nostr/unlink').status_code, 403)
        self.assertEqual(client.post('/api/logout').status_code, 403)
        self.assertEqual(client.post('/api/me/nostr/unlink', headers=SAME_SITE).status_code, 200)

    def test_nostr_rejects_a_bad_npub_without_sending_anything(self):
        os.environ['NOSTR_NSEC'] = os.environ.get('NOSTR_NSEC') or 'nsec1vl029mgpspedva04g90vltkh6fvh240zqtv9k0t9af8935ke9laqsnlfe5'
        r = self.logged_in().post('/api/me/nostr/start', json={'npub': 'not-an-npub'}, headers=SAME_SITE)
        self.assertEqual(r.status_code, 200)
        self.assertFalse(r.json()['ok'])

    def test_games_catalogue_needs_login_and_filters(self):
        self.assertEqual(self.anonymous().get('/api/games').status_code, 401)
        self.assertEqual(self.anonymous().get('/api/games/1').status_code, 401)
        client = self.logged_in()
        r = client.get('/api/games', params={'platform': 'PS1', 'per_page': 5})
        self.assertEqual(r.status_code, 200)
        body = r.json()
        self.assertLessEqual(len(body['items']), 5)
        self.assertTrue(all('PS1' in g['platforms'] for g in body['items']))
        self.assertEqual(client.get('/api/games/99999999').status_code, 404)
        if body['items']:
            one = client.get(f"/api/games/{body['items'][0]['id']}").json()
            self.assertNotIn('message_link', one)



if __name__ == '__main__':
    unittest.main()


class TestEquipmentAndGuild(unittest.TestCase):
    OTHER = 880012

    @classmethod
    def setUpClass(cls):
        from models.equipment import Equipment, UserEquipment
        from models.guild import Guild, GuildMember
        cls.client = TestClient(app, follow_redirects=False)
        cls.client.__enter__()
        session = Database().get_session()
        for uid in (USER_ID + 100, cls.OTHER):
            session.query(UserEquipment).filter_by(user_id=uid).delete()
            session.query(GuildMember).filter_by(user_id=uid).delete()
            session.query(Utente).filter_by(id_telegram=uid).delete()
        session.query(Guild).filter_by(name='Gilda di prova').delete()
        session.commit()
        cls.uid = USER_ID + 100
        for uid, name, pts in ((cls.uid, 'eqtest', 500), (cls.OTHER, 'guest', 0)):
            session.add(Utente(id_telegram=uid, username=name, nome=name, exp=0, points=pts, livello=3, premium=0,
                               livello_selezionato=1))
        session.commit()
        # a fresh test database has no catalogue seeded: two helmets of its own
        session.query(Equipment).filter(Equipment.name.like('Elmo di prova%')).delete(synchronize_session=False)
        for n in (1, 2):
            session.add(Equipment(name=f'Elmo di prova {n}', slot='head', rarity=n + 1, min_level=1, stats_json={'health': 5 * n}))
        session.commit()
        cls.items = [e.id for e in session.query(Equipment).filter(Equipment.name.like('Elmo di prova%')).all()]
        for eid in cls.items:
            session.add(UserEquipment(user_id=cls.uid, equipment_id=eid))
        session.commit()
        session.close()

    @classmethod
    def tearDownClass(cls):
        from models.equipment import UserEquipment
        from models.guild import Guild, GuildMember
        session = Database().get_session()
        from models.equipment import Equipment
        session.query(UserEquipment).filter_by(user_id=cls.uid).delete()
        session.query(Equipment).filter(Equipment.name.like('Elmo di prova%')).delete(synchronize_session=False)
        session.query(GuildMember).filter(GuildMember.user_id.in_([cls.uid, cls.OTHER])).delete(synchronize_session=False)
        session.query(Guild).filter_by(name='Gilda di prova').delete()
        session.query(Utente).filter(Utente.id_telegram.in_([cls.uid, cls.OTHER])).delete(synchronize_session=False)
        session.commit()
        session.close()
        cls.client.__exit__(None, None, None)

    def as_user(self, uid):
        client = TestClient(app, follow_redirects=False)
        client.cookies.set(auth.COOKIE, auth.make_session(uid))
        return client

    def test_both_need_login_and_writes_need_the_app_header(self):
        anon = TestClient(app, follow_redirects=False)
        for path in ('/api/me/equipment', '/api/me/guild'):
            self.assertEqual(anon.get(path).status_code, 401)
        me = self.as_user(self.uid)
        self.assertEqual(me.post('/api/me/equipment/equip', json={'id': 1}).status_code, 403)
        self.assertEqual(me.post('/api/me/guild', json={'action': 'deposit', 'amount': 1}).status_code, 403)

    def test_wearing_and_taking_off(self):
        me = self.as_user(self.uid)
        state = me.get('/api/me/equipment').json()
        self.assertEqual(len(state['items']), len(self.items))
        first = state['items'][0]['id']
        worn = me.post('/api/me/equipment/equip', json={'id': first}, headers=SAME_SITE).json()
        self.assertTrue(worn['ok'])
        self.assertEqual([i['id'] for i in worn['items'] if i['equipped']], [first])
        off = me.post('/api/me/equipment/unequip', json={'id': first}, headers=SAME_SITE).json()
        self.assertTrue(off['ok'])
        self.assertFalse(any(i['equipped'] for i in off['items']))

    def test_nobody_touches_somebody_elses_items(self):
        mine = self.as_user(self.uid).get('/api/me/equipment').json()['items'][0]['id']
        r = self.as_user(self.OTHER).post('/api/me/equipment/equip', json={'id': mine}, headers=SAME_SITE).json()
        self.assertFalse(r['ok'])

    def test_guild_deposit_join_and_leader_only_actions(self):
        from models.guild import Guild, GuildMember
        session = Database().get_session()
        g = Guild(name='Gilda di prova', leader_id=self.uid, wumpa_bank=0, member_limit=5)
        session.add(g)
        session.flush()
        session.add(GuildMember(guild_id=g.id, user_id=self.uid, role='Leader'))
        session.commit()
        gid = g.id
        session.close()
        leader, guest = self.as_user(self.uid), self.as_user(self.OTHER)
        state = guest.get('/api/me/guild').json()
        self.assertIsNone(state['guild'])
        self.assertIn(gid, [x['id'] for x in state['guilds']])
        joined = guest.post('/api/me/guild', json={'action': 'join', 'guild_id': gid}, headers=SAME_SITE).json()
        self.assertTrue(joined['ok'])
        self.assertEqual(len(joined['guild']['members']), 2)
        self.assertTrue(all(m['img'] for m in joined['guild']['members']))
        village = next(b for b in joined['guild']['buildings'] if b['key'] == 'village')
        self.assertEqual(village['img'], 'main')
        self.assertEqual(self.client.get('/img/guild/main/256.webp').status_code, 200)
        self.assertEqual(self.client.get('/img/guild/nope/256.webp').status_code, 404)
        # a member cannot upgrade or withdraw
        for body in ({'action': 'upgrade', 'building': 'inn'}, {'action': 'withdraw', 'amount': 1}):
            self.assertFalse(guest.post('/api/me/guild', json=body, headers=SAME_SITE).json()['ok'])
        paid = leader.post('/api/me/guild', json={'action': 'deposit', 'amount': 120}, headers=SAME_SITE).json()
        self.assertTrue(paid['ok'])
        self.assertEqual((paid['guild']['bank'], paid['wumpa']), (120, 380))
        poor = leader.post('/api/me/guild', json={'action': 'deposit', 'amount': 10 ** 6}, headers=SAME_SITE).json()
        self.assertFalse(poor['ok'])
        # the game says what an upgrade costs when the bank is short
        short = leader.post('/api/me/guild', json={'action': 'upgrade', 'building': 'inn'}, headers=SAME_SITE).json()
        self.assertFalse(short['ok'])
        self.assertIn('Wumpa', short['message'])
        self.assertFalse(leader.post('/api/me/guild', json={'action': 'upgrade', 'building': 'nope'}, headers=SAME_SITE).json()['ok'])
        self.assertTrue(guest.post('/api/me/guild', json={'action': 'leave'}, headers=SAME_SITE).json()['ok'])


class TestStatChartAndSoloDungeon(unittest.TestCase):
    UID = USER_ID + 300

    @classmethod
    def setUpClass(cls):
        session = Database().get_session()
        session.query(Utente).filter_by(id_telegram=cls.UID).delete()
        session.add(Utente(id_telegram=cls.UID, username='alloc', nome='alloc', exp=0, points=0, livello=10, premium=0,
                           livello_selezionato=1, stat_points=6))
        session.commit()
        session.close()

    @classmethod
    def tearDownClass(cls):
        session = Database().get_session()
        session.query(Utente).filter_by(id_telegram=cls.UID).delete()
        session.commit()
        session.close()

    def client(self):
        c = TestClient(app, follow_redirects=False)
        c.cookies.set(auth.COOKIE, auth.make_session(self.UID))
        return c

    def test_chart_scale_is_fixed_and_grows_with_level(self):
        from webapp import data
        low, high = data.radar({'max_health': 100}, 1), data.radar({'max_health': 100}, 100)
        self.assertEqual([a['max'] for a in low], [a['max'] for a in high])  # same scale for everyone
        self.assertTrue(all(a['now'] <= a['max'] for a in high))
        self.assertTrue(all(l['now'] < h['now'] for l, h in zip(low, high) if l['key'] in ('max_health', 'base_damage')))
        beyond = data.radar({}, 193)  # past the cap the ceiling stops growing
        self.assertEqual([a['now'] for a in beyond], [a['now'] for a in high])
        self.assertEqual(next(a for a in high if a['key'] == 'resistance')['max'], 75)

    def test_spending_points_goes_through_the_game_rule(self):
        c = self.client()
        self.assertEqual(c.post('/api/me/stats/allocate', json={'stat': 'damage'}).status_code, 403)
        r = c.post('/api/me/stats/allocate', json={'stat': 'damage', 'count': 200}, headers=SAME_SITE).json()
        self.assertTrue(r['ok'])
        self.assertEqual((r['profile']['stat_points'], r['profile']['allocated']['damage']), (0, 6))
        self.assertEqual(len(r['profile']['radar']), 6)
        none_left = c.post('/api/me/stats/allocate', json={'stat': 'crit'}, headers=SAME_SITE).json()
        self.assertFalse(none_left['ok'])
        self.assertFalse(c.post('/api/me/stats/allocate', json={'stat': 'nope'}, headers=SAME_SITE).json()['ok'])

    def test_solo_dungeon_opens_a_lobby_and_messages_the_player(self):
        from unittest import mock
        from models.dungeon import Dungeon
        c = self.client()
        listed = c.get('/api/dungeons').json()
        if not listed:
            self.skipTest('no dungeon defined in this database')
        first = listed[0]['id']
        with mock.patch('urllib.request.urlopen') as sent:
            r = c.post('/api/dungeons/start', json={'id': first}, headers=SAME_SITE).json()
        self.assertTrue(r['ok'], r)
        body = sent.call_args[0][0].data.decode()
        self.assertIn('dungeon_start|', body)
        self.assertIn(str(self.UID), body)
        session = Database().get_session()
        lobby = session.query(Dungeon).filter_by(chat_id=self.UID, status='registration').first()
        self.assertTrue(lobby and lobby.is_solo)
        session.query(Dungeon).filter_by(chat_id=self.UID).delete()
        session.commit()
        session.close()


class TestBuildTitleAndBuildings(unittest.TestCase):
    UID = USER_ID + 400

    @classmethod
    def setUpClass(cls):
        from models.guild import Guild, GuildMember
        session = Database().get_session()
        session.query(GuildMember).filter_by(user_id=cls.UID).delete()
        session.query(Guild).filter_by(name='Gilda edifici').delete()
        session.query(Utente).filter_by(id_telegram=cls.UID).delete()
        session.add(Utente(id_telegram=cls.UID, username='bld', nome='bld', exp=0, points=900, livello=10, premium=0,
                           livello_selezionato=1, stat_points=20, titles='["Eroe"]'))
        session.flush()
        g = Guild(name='Gilda edifici', leader_id=cls.UID, wumpa_bank=0, member_limit=5, inn_level=1, ancient_temple_level=1,
                  garden_level=1, laboratory_level=1, brewery_level=0)
        session.add(g)
        session.flush()
        session.add(GuildMember(guild_id=g.id, user_id=cls.UID, role='Leader'))
        session.commit()
        session.close()

    @classmethod
    def tearDownClass(cls):
        from models.guild import Guild, GuildMember
        session = Database().get_session()
        session.query(GuildMember).filter_by(user_id=cls.UID).delete()
        session.query(Guild).filter_by(name='Gilda edifici').delete()
        session.query(Utente).filter_by(id_telegram=cls.UID).delete()
        session.commit()
        session.close()

    def client(self):
        c = TestClient(app, follow_redirects=False)
        c.cookies.set(auth.COOKIE, auth.make_session(self.UID))
        return c

    def test_build_can_be_changed_taken_back_and_preset(self):
        c = self.client()
        r = c.post('/api/me/stats/build', json={'allocations': {'damage': 12, 'crit': 8}}, headers=SAME_SITE).json()
        self.assertTrue(r['ok'], r)
        self.assertEqual((r['profile']['stat_points'], r['profile']['allocated']['damage']), (0, 12))
        back = c.post('/api/me/stats/build', json={'allocations': {'damage': 2}}, headers=SAME_SITE).json()
        self.assertEqual((back['profile']['stat_points'], back['profile']['allocated']['crit']), (18, 0))
        self.assertFalse(c.post('/api/me/stats/build', json={'allocations': {'damage': 99}}, headers=SAME_SITE).json()['ok'])
        self.assertFalse(c.post('/api/me/stats/build', json={'allocations': {'resistance': 76}}, headers=SAME_SITE).json()['ok'])
        preset = c.post('/api/me/stats/build', json={'preset': 'Tank'}, headers=SAME_SITE).json()
        self.assertTrue(preset['ok'])
        self.assertEqual(preset['profile']['stat_points'], 0)
        self.assertTrue(preset['profile']['allocated']['health'] > 0)

    def test_title_is_chosen_from_the_owned_ones(self):
        c = self.client()
        self.assertTrue(c.post('/api/me/title', json={'title': 'Eroe'}, headers=SAME_SITE).json()['profile']['title'] == 'Eroe')
        self.assertFalse(c.post('/api/me/title', json={'title': 'Re del mondo'}, headers=SAME_SITE).json()['ok'])
        self.assertIsNone(c.post('/api/me/title', json={'title': None}, headers=SAME_SITE).json()['profile']['title'])

    def test_every_building_says_what_can_be_pressed(self):
        c = self.client()
        state = c.get('/api/me/guild').json()['guild']
        by = {b['key']: b for b in state['buildings']}
        self.assertEqual([x['action'] for x in by['inn']['use']], ['rest'])
        self.assertTrue(by['inn']['use'][0]['enabled'])
        self.assertEqual(by['ancient_temple']['use'][0]['action'], 'pray')
        self.assertEqual(by['garden']['use'][0]['action'], 'open')
        self.assertEqual(by['brewery']['use'], [])  # not built: nothing to press
        rest = c.post('/api/me/guild', json={'action': 'rest'}, headers=SAME_SITE).json()
        self.assertTrue(rest['ok'], rest)
        inn = next(b for b in rest['guild']['buildings'] if b['key'] == 'inn')
        self.assertEqual(inn['use'][0]['action'], 'wake')
        self.assertTrue(c.post('/api/me/guild', json={'action': 'wake'}, headers=SAME_SITE).json()['ok'])

    def test_garden_and_laboratory_panels(self):
        c = self.client()
        for kind in ('garden', 'laboratory'):
            r = c.post('/api/me/guild', json={'action': 'workshop', 'building': kind}, headers=SAME_SITE).json()
            self.assertEqual(r['workshop']['kind'], kind)


class TestAlchemyClaim(unittest.TestCase):
    UID = USER_ID + 500

    def test_ready_potions_can_be_claimed(self):
        from datetime import datetime, timedelta
        from models.alchemy import AlchemyQueue
        from services.alchemy_service import AlchemyService
        session = Database().get_session()
        session.query(AlchemyQueue).filter_by(user_id=self.UID).delete()
        session.query(Utente).filter_by(id_telegram=self.UID).delete()
        session.add(Utente(id_telegram=self.UID, username='alc', nome='alc', exp=0, points=0, livello=5, premium=0, livello_selezionato=1))
        session.flush()
        session.add(AlchemyQueue(user_id=self.UID, potion_name='Pozione Media', completion_time=datetime.now() - timedelta(minutes=1),
                                 status='in_progress', xp_gain=20))
        session.commit()
        session.close()
        try:
            ok, message = AlchemyService().claim_potions(self.UID)
            self.assertTrue(ok, message)
            self.assertIn('XP Alchimia', message)
            self.assertFalse(AlchemyService().claim_potions(self.UID)[0])  # nothing left to claim
        finally:
            session = Database().get_session()
            session.query(AlchemyQueue).filter_by(user_id=self.UID).delete()
            session.query(Utente).filter_by(id_telegram=self.UID).delete()
            session.commit()
            session.close()


class TestMarketGuidesEggs(unittest.TestCase):
    SELLER, BUYER = USER_ID + 600, USER_ID + 601

    @classmethod
    def setUpClass(cls):
        from models.market import MarketListing
        session = Database().get_session()
        session.query(MarketListing).filter(MarketListing.seller_id.in_([cls.SELLER, cls.BUYER])).delete(synchronize_session=False)
        session.query(Utente).filter(Utente.id_telegram.in_([cls.SELLER, cls.BUYER])).delete(synchronize_session=False)
        for uid, pts in ((cls.SELLER, 0), (cls.BUYER, 50)):
            session.add(Utente(id_telegram=uid, username=f'mk{uid}', nome=f'mk{uid}', exp=0, points=pts, livello=5, premium=0, livello_selezionato=1))
        session.flush()
        from datetime import datetime, timedelta
        session.add(MarketListing(seller_id=cls.SELLER, item_name='Spada di prova', quantity=1, price_per_unit=999999,
                                  expires_at=datetime.now() + timedelta(days=1), status='active'))
        session.commit()
        session.close()

    @classmethod
    def tearDownClass(cls):
        from models.market import MarketListing
        session = Database().get_session()
        session.query(MarketListing).filter(MarketListing.seller_id.in_([cls.SELLER, cls.BUYER])).delete(synchronize_session=False)
        session.query(Utente).filter(Utente.id_telegram.in_([cls.SELLER, cls.BUYER])).delete(synchronize_session=False)
        session.commit()
        session.close()

    def as_user(self, uid):
        c = TestClient(app, follow_redirects=False)
        c.cookies.set(auth.COOKIE, auth.make_session(uid))
        return c

    def test_market_search_and_the_rules_of_buying(self):
        buyer, seller = self.as_user(self.BUYER), self.as_user(self.SELLER)
        found = buyer.get('/api/market', params={'q': 'spada di pro'}).json()
        self.assertEqual([l['item'] for l in found['listings']], ['Spada di prova'])
        self.assertEqual(buyer.get('/api/market', params={'q': 'nessuno-vende-questo'}).json()['total'], 0)
        listing = found['listings'][0]
        self.assertFalse(listing['mine'])
        self.assertTrue(seller.get('/api/market', params={'q': 'spada'}).json()['listings'][0]['mine'])
        self.assertEqual(self.as_user(self.BUYER).get('/api/market').status_code, 200)
        self.assertEqual(TestClient(app).get('/api/market').status_code, 401)
        poor = buyer.post('/api/me/guild', json={'action': 'market_buy', 'option': str(listing['id'])}, headers=SAME_SITE).json()
        self.assertFalse(poor['ok'])  # 50 Wumpa against 999999

    def test_guides_are_listed_and_readable(self):
        c = self.as_user(self.BUYER)
        keys = [g['key'] for g in c.get('/api/guides').json()]
        self.assertIn('dragon_eggs', keys)
        self.assertNotIn('purchase_game', keys)
        self.assertIn('Stalle dei draghi', c.get('/api/guides/dragon_eggs').json()['text'])
        self.assertEqual(c.get('/api/guides/purchase_game').status_code, 404)
        self.assertEqual(c.get('/api/guides/..%2Fsettings').status_code, 404)


class TestInventoryGuildForge(unittest.TestCase):
    BOSS, SMITH = USER_ID + 700, USER_ID + 701

    @classmethod
    def setUpClass(cls):
        from models.guild import Guild, GuildMember
        session = Database().get_session()
        session.query(GuildMember).filter(GuildMember.user_id.in_([cls.BOSS, cls.SMITH])).delete(synchronize_session=False)
        session.query(Guild).filter(Guild.name.like('Test Forge%')).delete(synchronize_session=False)
        session.query(Utente).filter(Utente.id_telegram.in_([cls.BOSS, cls.SMITH])).delete(synchronize_session=False)
        for uid in (cls.BOSS, cls.SMITH):
            session.add(Utente(id_telegram=uid, username=f'fg{uid}', nome=f'fg{uid}', exp=0, points=100000, livello=30, premium=0, livello_selezionato=1))
        session.commit()
        session.close()

    @classmethod
    def tearDownClass(cls):
        from models.guild import Guild, GuildMember
        session = Database().get_session()
        session.query(GuildMember).filter(GuildMember.user_id.in_([cls.BOSS, cls.SMITH])).delete(synchronize_session=False)
        session.query(Guild).filter(Guild.name.like('Test Forge%')).delete(synchronize_session=False)
        session.query(Utente).filter(Utente.id_telegram.in_([cls.BOSS, cls.SMITH])).delete(synchronize_session=False)
        session.commit()
        session.close()

    def as_user(self, uid):
        c = TestClient(app, follow_redirects=False)
        c.cookies.set(auth.COOKIE, auth.make_session(uid))
        return c

    def test_inventory_and_transformations_answer(self):
        c = self.as_user(self.BOSS)
        inv = c.get('/api/me/inventory')
        self.assertEqual(inv.status_code, 200)
        self.assertEqual(c.get('/api/me/transformations').status_code, 200)
        self.assertFalse(c.post('/api/me/inventory/use', json={'name': 'Oggetto inesistente'}, headers=SAME_SITE).json()['ok'])
        self.assertFalse(c.post('/api/me/inventory/upgrade', json={'id': 3, 'count': 1}, headers=SAME_SITE).json()['ok'])
        self.assertEqual(c.post('/api/me/inventory/use', json={'name': 'x'}).status_code, 403)

    def test_character_picking_refuses_what_is_not_owned(self):
        c = self.as_user(self.BOSS)
        r = c.post('/api/me/character', json={'id': 999999}, headers=SAME_SITE).json()
        self.assertFalse(r['ok'])

    def test_guild_management_and_forge(self):
        c = self.as_user(self.BOSS)
        act = lambda **kw: c.post('/api/me/guild', json=kw, headers=SAME_SITE).json()
        made = act(action='found', option='Test Forge Guild')
        self.assertTrue(made['ok'], made)
        self.assertTrue(act(action='rename', option='Test Forge Due')['ok'])
        self.assertTrue(act(action='describe', option='Una gilda di prova')['ok'])
        body = act(action='workshop', building='armory').get('workshop')
        self.assertEqual(body['kind'], 'armory')
        self.assertIn('items', body)
        nothing = act(action='craft_claim')
        self.assertFalse(nothing['ok'])
        self.assertFalse(act(action='craft', option='999999')['ok'])
        self.assertTrue(act(action='disband')['ok'])
