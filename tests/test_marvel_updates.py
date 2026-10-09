import unittest
from database import Database
from models.user import Utente
from models.dungeon import Dungeon, DungeonParticipant
from services.dungeon_service import DungeonService
from services.season_gate import get_active_season_theme
import datetime
from sqlalchemy import text

class TestMarvelUpdates(unittest.TestCase):
    def setUp(self):
        self.db = Database()
        self.dungeon_service = DungeonService()
        session = self.db.get_session()
        
        # Clean up
        session.query(DungeonParticipant).delete()
        session.query(Dungeon).delete()
        session.query(Utente).filter(Utente.id_telegram == 13999).delete()
        session.commit()
        
        # Create test user
        user = Utente(id_telegram=13999, username="test_marvel", nome="Test Marvel")
        session.add(user)
        session.commit()
        session.close()

    def test_seasonal_dungeon_filter(self):
        """Verify that only dungeons matching the active theme are returned."""
        session = self.db.get_session()
        theme = get_active_season_theme(session)
        
        # Get active IDs from service
        active_ids = self.dungeon_service.get_active_dungeon_ids(session=session)
        
        # Between seasons nothing is gated
        if not theme:
            self.assertEqual(active_ids, sorted(self.dungeon_service.dungeons_cache.keys()))
            session.close()
            return
        
        # Verify all returned dungeons match the theme
        for d_id in active_ids:
            d_def = self.dungeon_service.dungeons_cache.get(d_id)
            self.assertEqual(d_def.get('saga').strip().lower(), theme.strip().lower())
        
        # Verify no other dungeons are returned
        for d_id, d_def in self.dungeon_service.dungeons_cache.items():
            if d_def.get('saga').strip().lower() != theme.strip().lower():
                self.assertNotIn(d_id, active_ids)
        
        session.close()

    def test_daily_solo_limit_strict(self):
        """Verify that solo dungeon attempts (including failed/expired) block subsequent attempts."""
        chat_id = 139991
        dungeon_def_id = 1 # Saga Saiyan
        user_id = 13999
        
        # 1. Create a failed solo dungeon for today
        session = self.db.get_session()
        d_failed = Dungeon(
            name="Failed Solo",
            chat_id=chat_id,
            dungeon_def_id=dungeon_def_id,
            is_solo=True,
            status="failed",
            created_at=datetime.datetime.now(),
            start_time=datetime.datetime.now()
        )
        session.add(d_failed)
        session.flush()
        
        participant = DungeonParticipant(dungeon_id=d_failed.id, user_id=user_id)
        session.add(participant)
        session.commit()
        
        # 2. Try to create another solo dungeon of the same type
        # It should fail because there's already a 'failed' one today
        success, msg = self.dungeon_service.create_dungeon(chat_id, dungeon_def_id, user_id, is_solo=True)
        self.assertFalse(success)
        self.assertIn("già tentato", msg.lower())
        
        session.close()

    def test_daily_solo_limit_start_dungeon(self):
        """Verify that start_dungeon also enforces the limit if it becomes solo."""
        chat_id = 139992
        dungeon_def_id = 1
        user_id = 13999
        
        # 1. Create a previous expired solo dungeon today
        session = self.db.get_session()
        d_expired = Dungeon(
            name="Expired Solo",
            chat_id=chat_id - 1, # Different chat
            dungeon_def_id=dungeon_def_id,
            is_solo=True,
            status="expired",
            created_at=datetime.datetime.now(),
            start_time=datetime.datetime.now()
        )
        session.add(d_expired)
        session.flush()
        session.add(DungeonParticipant(dungeon_id=d_expired.id, user_id=user_id))
        session.commit()
        
        # 2. Creating it again today is refused outright...
        success, msg = self.dungeon_service.create_dungeon(chat_id, dungeon_def_id, user_id, is_solo=False)
        self.assertFalse(success)
        self.assertIn("Ritorna domani", msg)

        # 3. ...and a lobby that got around that (opened before, or by another path) still cannot start.
        lobby = Dungeon(name="Lobby", chat_id=chat_id, dungeon_def_id=dungeon_def_id, status="registration",
                        is_solo=False, created_at=datetime.datetime.now())
        session.add(lobby)
        session.flush()
        session.add(DungeonParticipant(dungeon_id=lobby.id, user_id=user_id))
        session.commit()
        success, msg, events = self.dungeon_service.start_dungeon(chat_id)
        self.assertFalse(success)
        self.assertIn("Ritorna domani", msg)

        session.close()

    def _played(self, status, def_id=1, chat_id=139993, started=True, days_ago=0):
        """A dungeon this player ran (or only opened) at some point."""
        session = self.db.get_session()
        when = datetime.datetime.now() - datetime.timedelta(days=days_ago)
        d = Dungeon(name="Earlier run", chat_id=chat_id, dungeon_def_id=def_id, status=status, is_solo=False,
                    created_at=when, start_time=when if started else None)
        session.add(d)
        session.flush()
        session.add(DungeonParticipant(dungeon_id=d.id, user_id=13999))
        session.commit()
        session.close()

    def test_once_a_day_whether_you_win_or_lose(self):
        for status in ("completed", "failed", "expired", "fled"):
            self.setUp()
            self._played(status)
            session = self.db.get_session()
            self.assertTrue(self.dungeon_service.has_played_today(session, 13999, 1), status)
            session.close()

    def test_group_dungeons_count_too(self):
        """Joining the group's lobby for a dungeon already played today is refused."""
        self._played("completed", chat_id=139994)
        lobby_chat = 139995
        session = self.db.get_session()
        session.add(Dungeon(name="Lobby", chat_id=lobby_chat, dungeon_def_id=1, status="registration", is_solo=False,
                            created_at=datetime.datetime.now()))
        session.commit()
        session.close()
        ok, msg = self.dungeon_service.join_dungeon(lobby_chat, 13999)
        self.assertFalse(ok)
        self.assertIn("già tentato", msg.lower())

    def test_a_different_dungeon_is_still_open(self):
        self._played("completed", def_id=1)
        session = self.db.get_session()
        self.assertFalse(self.dungeon_service.has_played_today(session, 13999, 2))
        session.close()

    def test_tomorrow_it_is_open_again(self):
        self._played("completed", days_ago=1)
        session = self.db.get_session()
        self.assertFalse(self.dungeon_service.has_played_today(session, 13999, 1))
        session.close()

    def test_a_lobby_that_never_started_is_not_an_attempt(self):
        self._played("failed", started=False)  # e.g. cleaned up after nobody pressed start
        self._played("registration", started=False, chat_id=139996)
        session = self.db.get_session()
        self.assertFalse(self.dungeon_service.has_played_today(session, 13999, 1))
        session.close()



if __name__ == "__main__":
    unittest.main()
