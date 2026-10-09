import os
import sys
import types
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import Database
from models.user import Utente
from utils import ghost_cleanup

IDS = {'member': 990001, 'left': 990002, 'not_found': 990003, 'rate_limited': 990004, 'bad_token': 990005}


class FakeBot:
    def get_chat_member(self, chat, user_id):
        if user_id == IDS['member']:
            return types.SimpleNamespace(status='member')
        if user_id == IDS['left']:
            return types.SimpleNamespace(status='left')
        if user_id == IDS['not_found']:
            raise Exception("Bad Request: user not found")
        if user_id == IDS['rate_limited']:
            raise Exception("Too Many Requests: retry after 30")
        raise Exception("Unauthorized")


class TestGhostCleanupSafety(unittest.TestCase):
    def setUp(self):
        self.db = Database()
        session = self.db.get_session()
        session.query(Utente).filter(Utente.id_telegram.in_(list(IDS.values()))).delete()
        for name, uid in IDS.items():
            session.add(Utente(id_telegram=uid, username=f"ghost_{name}", nome=name, exp=0, points=0, livello=1, premium=0))
        session.commit()
        session.close()
        self._test = ghost_cleanup.TEST
        ghost_cleanup.TEST = 0  # the cleanup only runs in production mode

    def tearDown(self):
        ghost_cleanup.TEST = self._test
        session = self.db.get_session()
        session.query(Utente).filter(Utente.id_telegram.in_(list(IDS.values()))).delete()
        session.commit()
        session.close()

    def remaining(self):
        session = self.db.get_session()
        try:
            return {u.id_telegram for u in session.query(Utente).filter(Utente.id_telegram.in_(list(IDS.values()))).all()}
        finally:
            session.close()

    def test_only_players_telegram_says_are_gone_are_removed(self):
        ghost_cleanup.cleanup_ghost_users(FakeBot())
        kept = self.remaining()
        self.assertIn(IDS['member'], kept)
        self.assertNotIn(IDS['left'], kept)
        self.assertNotIn(IDS['not_found'], kept)

    def test_a_failing_check_never_deletes_anyone(self):
        ghost_cleanup.cleanup_ghost_users(FakeBot())
        kept = self.remaining()
        self.assertIn(IDS['rate_limited'], kept, "a rate limit says nothing about the player")
        self.assertIn(IDS['bad_token'], kept, "a wrong token says nothing about the player")


if __name__ == '__main__':
    unittest.main()
