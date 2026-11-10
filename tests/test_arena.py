import hashlib
import hmac
import json
import os
import sys
import threading
import time
import unittest
from datetime import datetime, timedelta
from unittest import mock
from urllib.parse import urlencode

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from fastapi.testclient import TestClient
except Exception as e:  # the test client needs its HTTP library installed (see requirements.dev.txt)
    raise unittest.SkipTest(f"fastapi test client unavailable: {e}")

from database import Database
from models.combat import CombatParticipation
from models.pve import Mob
from models.user import Utente
from models.webapp import WebCombatAction
from services import web_actions
from settings import BOT_TOKEN
from webapp import auth, combat
from webapp.app import app

USER_ID = 880077
STRANGER_CHAT = -100880077
SAME_SITE = {'X-Requested-With': 'aroma'}
MOB_NAMES = ('Arena Uno', 'Arena Due', 'Arena Privato', 'Arena Altrove')


def init_data(user_id, token=BOT_TOKEN, age=0):
    fields = {'auth_date': str(int(time.time()) - age), 'query_id': 'AAE', 'user': json.dumps({'id': user_id})}
    check = "\n".join(f"{k}={v}" for k, v in sorted(fields.items()))
    secret = hmac.new(b"WebAppData", token.encode(), hashlib.sha256).digest()
    fields['hash'] = hmac.new(secret, check.encode(), hashlib.sha256).hexdigest()
    return urlencode(fields)


def clean(session):
    mob_ids = [m.id for m in session.query(Mob).filter(Mob.name.in_(MOB_NAMES)).all()]
    if mob_ids:
        session.query(CombatParticipation).filter(CombatParticipation.mob_id.in_(mob_ids)).delete(synchronize_session=False)
    session.query(CombatParticipation).filter_by(user_id=USER_ID).delete()
    session.query(Mob).filter(Mob.name.in_(MOB_NAMES)).delete(synchronize_session=False)
    session.query(WebCombatAction).filter_by(user_id=USER_ID).delete()
    session.query(Utente).filter_by(id_telegram=USER_ID).delete()
    session.commit()


class ArenaCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app, follow_redirects=False)
        cls.client.__enter__()  # runs the startup hook (creates the web tables)

    @classmethod
    def tearDownClass(cls):
        cls.client.__exit__(None, None, None)

    def setUp(self):
        self.group = combat._group_id()
        session = Database().get_session()
        clean(session)
        session.add(Utente(id_telegram=USER_ID, username='arenatest', nome='Arena Test', exp=0, points=0, livello=10,
                           premium=0, livello_selezionato=1, health=100, max_health=100, current_hp=60, mana=40,
                           max_mana=50, speed=20, last_attack_time=datetime.now() - timedelta(hours=1)))
        for name, chat, health in (('Arena Uno', self.group, 50), ('Arena Due', self.group, 200),
                                   ('Arena Privato', USER_ID, 100), ('Arena Altrove', STRANGER_CHAT, 100)):
            session.add(Mob(name=name, health=health, max_health=200, attack_damage=10, chat_id=chat, speed=30))
        session.commit()
        self.mobs = {m.name: m.id for m in session.query(Mob).filter(Mob.name.in_(MOB_NAMES)).all()}
        session.close()

    def tearDown(self):
        session = Database().get_session()
        clean(session)
        session.close()

    def logged_in(self):
        client = TestClient(app, follow_redirects=False)
        client.cookies.set(auth.COOKIE, auth.make_session(USER_ID))
        return client


class TestTelegramLogin(ArenaCase):
    def test_signed_data_names_the_user(self):
        self.assertEqual(auth.telegram_user(init_data(USER_ID)), USER_ID)

    def test_another_bots_signature_tampering_and_old_data_are_refused(self):
        self.assertIsNone(auth.telegram_user(init_data(USER_ID, token='1:other')))
        self.assertIsNone(auth.telegram_user(init_data(USER_ID).replace(str(USER_ID), '1')))
        self.assertIsNone(auth.telegram_user(init_data(USER_ID, age=auth.INIT_DATA_MAX_AGE + 60)))
        self.assertIsNone(auth.telegram_user('garbage'))
        self.assertIsNone(auth.telegram_user(''))

    def test_a_player_gets_a_session(self):
        client = TestClient(app, follow_redirects=False)
        r = client.post('/api/login/telegram', json={'init_data': init_data(USER_ID)}, headers=SAME_SITE)
        self.assertEqual(r.status_code, 200)
        self.assertEqual(auth.read_session(r.cookies.get(auth.COOKIE)), USER_ID)

    def test_unknown_people_and_bad_data_get_none(self):
        client = TestClient(app, follow_redirects=False)
        for data in (init_data(999000111), init_data(USER_ID, token='1:other')):
            r = client.post('/api/login/telegram', json={'init_data': data}, headers=SAME_SITE)
            self.assertEqual(r.status_code, 403)
            self.assertIsNone(r.cookies.get(auth.COOKIE))
        self.assertEqual(client.post('/api/login/telegram', json={'init_data': init_data(USER_ID)}).status_code, 403)


class TestArenaState(ArenaCase):
    def test_needs_login(self):
        self.assertEqual(TestClient(app).get('/api/combat').status_code, 401)

    def test_shows_the_group_and_the_players_own_mobs_only(self):
        state = self.logged_in().get('/api/combat').json()
        mine = {m['name']: m for m in state['mobs'] if m['name'] in MOB_NAMES}
        self.assertEqual(set(mine), {'Arena Uno', 'Arena Due', 'Arena Privato'})
        self.assertTrue(mine['Arena Privato']['private'])
        self.assertFalse(mine['Arena Uno']['private'])
        self.assertEqual(state['mobs'][0]['name'], 'Arena Privato')
        self.assertEqual(mine['Arena Uno']['hp_pct'], 25)
        self.assertTrue(mine['Arena Uno']['aoe'])       # two enemies in the group
        self.assertFalse(mine['Arena Privato']['aoe'])  # alone in the private chat

    def test_health_numbers_need_a_scouter(self):
        hidden = self.logged_in().get('/api/combat').json()
        self.assertFalse(hidden['player']['scouter'])
        self.assertTrue(all('hp' not in m and 'attack' not in m for m in hidden['mobs']))
        with mock.patch.object(combat, '_has_scouter', return_value=True):
            shown = {m['name']: m for m in self.logged_in().get('/api/combat').json()['mobs']}
        self.assertEqual((shown['Arena Uno']['hp'], shown['Arena Uno']['max_hp']), (50, 200))

    def test_player_state(self):
        player = self.logged_in().get('/api/combat').json()['player']
        self.assertEqual((player['hp'], player['max_hp'], player['mana'], player['max_mana']), (60, 100, 40, 50))
        self.assertEqual((player['cooldown'], player['ready_in']), (30.0, 0.0))

        session = Database().get_session()
        session.query(Utente).filter_by(id_telegram=USER_ID).update({'last_attack_time': datetime.now() - timedelta(seconds=10)})
        session.commit()
        session.close()
        self.assertAlmostEqual(self.logged_in().get('/api/combat').json()['player']['ready_in'], 20, delta=1)


class TestActionQueue(ArenaCase):
    def test_an_action_is_handed_out_once_and_answered(self):
        action_id = web_actions.enqueue(USER_ID, self.group, 'attack_enemy|mob|1')
        claimed = [a for a in web_actions.claim_pending() if a['id'] == action_id]
        self.assertEqual(claimed, [{'id': action_id, 'user_id': USER_ID, 'chat_id': self.group, 'data': 'attack_enemy|mob|1'}])
        self.assertEqual([a for a in web_actions.claim_pending() if a['id'] == action_id], [])
        web_actions.complete(action_id, True, "Colpito!")
        self.assertEqual(web_actions.wait_result(action_id, timeout=1), (True, "Colpito!"))

    def test_an_action_left_too_long_is_never_played(self):
        action_id = web_actions.enqueue(USER_ID, self.group, 'attack_enemy|mob|1')
        session = Database().get_session()
        session.query(WebCombatAction).filter_by(id=action_id).update({'created_at': datetime.now() - timedelta(minutes=1)})
        session.commit()
        session.close()
        self.assertEqual([a for a in web_actions.claim_pending() if a['id'] == action_id], [])
        self.assertIsNone(web_actions.wait_result(action_id, timeout=1))

    def test_giving_up_waiting_drops_the_action(self):
        action_id = web_actions.enqueue(USER_ID, self.group, 'attack_enemy|mob|1')
        self.assertIsNone(web_actions.wait_result(action_id, timeout=0.3, poll=0.05))
        self.assertEqual([a for a in web_actions.claim_pending() if a['id'] == action_id], [])


class TestArenaActions(ArenaCase):
    def play_the_bot(self, ok, message):
        """Stands in for the bot: answers the next action of this test's user."""
        seen = []

        def run():
            deadline = time.time() + 5
            while time.time() < deadline and not seen:
                for action in web_actions.claim_pending():
                    if action['user_id'] == USER_ID:
                        seen.append(action)
                        web_actions.complete(action['id'], ok, message)
                time.sleep(0.05)
        thread = threading.Thread(target=run, daemon=True)
        thread.start()
        return seen, thread

    def post(self, mob, action):
        return self.logged_in().post('/api/combat', json={'mob': mob, 'action': action}, headers=SAME_SITE)

    def test_a_button_reaches_the_bot_as_the_chats_own_callback(self):
        seen, thread = self.play_the_bot(True, "Hai inflitto 12 danni")
        r = self.post(self.mobs['Arena Uno'], 'attack').json()
        thread.join()
        self.assertEqual((r['ok'], r['message']), (True, "Hai inflitto 12 danni"))
        self.assertEqual(seen[0]['data'], f"attack_enemy|mob|{self.mobs['Arena Uno']}")
        self.assertEqual(seen[0]['chat_id'], self.group)
        self.assertIn('mobs', r)

    def test_a_private_mob_is_played_in_the_private_chat(self):
        seen, thread = self.play_the_bot(False, "Sei stanco!")
        r = self.post(self.mobs['Arena Privato'], 'scan').json()
        thread.join()
        self.assertEqual((r['ok'], r['message']), (False, "Sei stanco!"))
        self.assertEqual((seen[0]['data'], seen[0]['chat_id']), (f"scan_mob|{self.mobs['Arena Privato']}", USER_ID))

    def test_what_cannot_be_played_never_reaches_the_bot(self):
        for mob, action in ((self.mobs['Arena Altrove'], 'attack'), (self.mobs['Arena Uno'], 'explode'), (999999999, 'attack')):
            r = self.post(mob, action).json()
            self.assertFalse(r['ok'])
        session = Database().get_session()
        self.assertEqual(session.query(WebCombatAction).filter_by(user_id=USER_ID).count(), 0)
        session.close()

    def test_a_silent_bot_is_reported(self):
        with mock.patch.object(web_actions, 'wait_result', return_value=None):
            r = self.post(self.mobs['Arena Uno'], 'attack').json()
        self.assertFalse(r['ok'])
        self.assertIn('non risponde', r['message'])

    def test_requires_the_apps_own_header(self):
        r = self.logged_in().post('/api/combat', json={'mob': self.mobs['Arena Uno'], 'action': 'attack'})
        self.assertEqual(r.status_code, 403)


class TestBotPlaysWebActions(ArenaCase):
    """The bot's side: a web action runs through the chat's callback handler and its answer goes to the page."""

    def run_action(self, data, handler):
        import main
        action_id = web_actions.enqueue(USER_ID, self.group, data)
        action = next(a for a in web_actions.claim_pending() if a['id'] == action_id)
        with mock.patch.object(main, 'callback_query', side_effect=handler), \
                mock.patch.object(main.bot, 'answer_callback_query') as telegram:
            main.run_web_action(action)
        telegram.assert_not_called()
        return web_actions.wait_result(action_id, timeout=1)

    def test_the_call_looks_like_the_chats(self):
        import main
        calls = []
        self.run_action(f"attack_enemy|mob|{self.mobs['Arena Uno']}", calls.append)
        call = calls[0]
        self.assertTrue(main.is_web_call(call.id))
        self.assertEqual((call.from_user.id, call.message.chat.id, call.message.chat.type), (USER_ID, self.group, 'supergroup'))
        self.assertEqual(call.data, f"attack_enemy|mob|{self.mobs['Arena Uno']}")

    def test_a_hit_answers_with_what_it_did(self):
        import main

        def hit(call):
            main.safe_answer_callback(call.id, "⚔️ Attacco effettuato!")
            main.web_detail(call, "Hai inflitto **12** danni a Arena\\_Uno\n\n╔══🕹 ARENA UNO ══╗\n ❤️ Vita: 25%\n╚═════╝")
        self.assertEqual(self.run_action('attack_enemy|mob|1', hit), (True, "Hai inflitto 12 danni a Arena_Uno"))

    def test_a_refusal_is_not_ok_and_the_scouter_sheet_is(self):
        import main
        tired = lambda call: main.safe_answer_callback(call.id, "⏳ Sei stanco!", show_alert=True)
        self.assertEqual(self.run_action('attack_enemy|mob|1', tired), (False, "⏳ Sei stanco!"))
        sheet = lambda call: main.safe_answer_callback(call.id, "🔍 ANALISI SCOUTER: Arena Uno", show_alert=True)
        self.assertEqual(self.run_action('scan_mob|1', sheet), (True, "🔍 ANALISI SCOUTER: Arena Uno"))

    def test_a_crash_is_answered_too(self):
        def boom(call):
            raise RuntimeError("boom")
        ok, message = self.run_action('attack_enemy|mob|1', boom)
        self.assertFalse(ok)
        self.assertTrue(message)

    def test_a_real_attack_from_the_web_hurts_the_mob(self):
        import main
        mob_id = self.mobs['Arena Privato']
        action_id = web_actions.enqueue(USER_ID, USER_ID, f"attack_enemy|mob|{mob_id}")
        action = next(a for a in web_actions.claim_pending() if a['id'] == action_id)
        with mock.patch.object(main, 'bot'), mock.patch.object(main, 'send_combat_message') as card, \
                mock.patch.object(main, 'send_ephemeral_reply', return_value=False):
            main.run_web_action(action)
        ok, message = web_actions.wait_result(action_id, timeout=1)
        self.assertTrue(ok, message)
        self.assertTrue(card.called)  # the chat's card is refreshed exactly as after a button in the chat
        session = Database().get_session()
        self.assertLess(session.query(Mob).filter_by(id=mob_id).first().health, 100)
        session.close()


if __name__ == '__main__':
    unittest.main()
