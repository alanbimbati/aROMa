import unittest
from unittest.mock import patch, MagicMock
from database import Database
from models.user import Utente
from models.dungeon import Dungeon, DungeonParticipant
from services.dungeon_service import DungeonService
import datetime
import json

def frozen(moment):
    """A stand-in for the `datetime` class the service imports, whose now() is fixed."""
    class Frozen(datetime.datetime):
        @classmethod
        def now(cls, tz=None):
            return moment
    return Frozen


class TestDungeonScheduler(unittest.TestCase):
    def setUp(self):
        self.db = Database()
        self.dungeon_service = DungeonService()
        self.test_chat_id = 999999
        
        # Create test users
        session = self.db.get_session()
        
        # Clean up
        session.query(DungeonParticipant).delete()
        session.query(Dungeon).filter_by(chat_id=self.test_chat_id).delete()
        session.query(Utente).filter(Utente.id_telegram.in_([901, 902])).delete()
        
        u1 = Utente(id_telegram=901, username="UserOne", nome="One")
        u2 = Utente(id_telegram=902, username="UserTwo", nome="Two")
        session.add(u1)
        session.add(u2)
        session.commit()
        session.close()

    def tearDown(self):
        session = self.db.get_session()
        session.query(DungeonParticipant).delete()
        session.query(Dungeon).filter_by(chat_id=self.test_chat_id).delete()
        session.query(Utente).filter(Utente.id_telegram.in_([901, 902])).delete()
        session.commit()
        session.close()

    def test_schedule_creation(self):
        """Test that a dungeon is scheduled if none exists today"""
        # Set time to 10:00 AM
        fixed_now = datetime.datetime(2025, 1, 1, 10, 0, 0)

        # Mock random so we know the scheduled time (delay_mins = 30)
        with patch('services.dungeon_service.datetime', frozen(fixed_now)), patch('random.randint', return_value=30):
            self.dungeon_service.check_daily_dungeon_trigger(self.test_chat_id)
            
        # Verify DB
        session = self.db.get_session()
        # Find ANY registration dungeon for this chat
        dungeon = session.query(Dungeon).filter_by(chat_id=self.test_chat_id, status="registration").first()
        self.assertIsNotNone(dungeon, "Dungeon should be scheduled")
        self.assertEqual(dungeon.status, "registration")
        self.assertFalse(dungeon.is_hype_active)
        # Expected time: 10:00 + 30 mins = 10:30
        expected_time = datetime.datetime(2025, 1, 1, 10, 30, 0)
        self.assertEqual(dungeon.scheduled_for, expected_time)
        session.close()

    def test_hype_trigger(self):
        """Test that hype starts when scheduled time triggers"""
        # Setup: Dungeon scheduled for 12:00
        session = self.db.get_session()
        sched_time = datetime.datetime(2025, 1, 1, 12, 0, 0)
        d = Dungeon(
            name="Test Dungeon",
            chat_id=self.test_chat_id,
            dungeon_def_id=1,
            status="registration",
            scheduled_for=sched_time,
            is_hype_active=False,
            stats="{}"
        )
        session.add(d)
        session.commit()
        session.close()
        
        # Set time to 12:01
        fixed_now = datetime.datetime(2025, 1, 1, 12, 1, 0)

        with patch('services.dungeon_service.datetime', frozen(fixed_now)):
            result = self.dungeon_service.check_daily_dungeon_trigger(self.test_chat_id)
        
        self.assertEqual(result, "DUNGEON_PREANNOUNCED")
        
        # Verify DB
        session = self.db.get_session()
        d = session.query(Dungeon).filter_by(chat_id=self.test_chat_id).first()
        self.assertTrue(d.is_hype_active)
        # Hype start time should be set to now (approx)
        # Since we mocked datetime.now(), it should be exactly fixed_now? 
        # Yes if service calls datetime.datetime.now().
        # Except SQLAlchemy might use its own NOW function or python's. 
        # Unittest mock patch affects the module 'services.dungeon_service'.
        # So yes.
        self.assertEqual(d.hype_start_time, fixed_now)
        session.close()

    def test_auto_start_after_hype(self):
        """Test that the dungeon starts after hype with the users who joined during registration"""
        # Setup: Dungeon with hype active since 12:00
        session = self.db.get_session()
        hype_start = datetime.datetime(2025, 1, 1, 12, 0, 0)
        d = Dungeon(
            name="Test Dungeon",
            chat_id=self.test_chat_id,
            dungeon_def_id=1,
            status="registration",
            scheduled_for=hype_start,
            is_hype_active=True,
            hype_start_time=hype_start,
            total_stages=3,
            stats="{}"
        )
        session.add(d)
        session.commit()
        d_id = d.id
        # Only users who joined during registration take part: inactive ones are not pulled in
        session.add_all([DungeonParticipant(dungeon_id=d_id, user_id=901), DungeonParticipant(dungeon_id=d_id, user_id=902)])
        session.commit()
        session.close()
        
        # Set time to 12:06 (Hype duration is 2 mins)
        fixed_now = datetime.datetime(2025, 1, 1, 12, 6, 0)
        
        # Need to patch spawn_step to avoid implicit database calls needing real mob data
        # or we verify mob spawning separately.
        # But we want to test auto-join count.
        # Let's mock spawn_step.
        
        with patch('services.dungeon_service.datetime', frozen(fixed_now)), \
             patch.object(self.dungeon_service, 'spawn_step', return_value=([], [])) as mock_spawn:
            result = self.dungeon_service.check_daily_dungeon_trigger(self.test_chat_id)
            
            self.assertIsInstance(result, dict)
            self.assertEqual(result['type'], "DUNGEON_STARTED")
            self.assertEqual(result['participant_count'], 2)
            
            # Verify DB status
            session = self.db.get_session()
            d = session.query(Dungeon).filter_by(id=d_id).first()
            self.assertEqual(d.status, "active")
            self.assertEqual(d.current_stage, 1)
            
            # Verify participants
            parts = session.query(DungeonParticipant).filter_by(dungeon_id=d_id).all()
            part_ids = [p.user_id for p in parts]
            self.assertIn(901, part_ids)
            self.assertIn(902, part_ids)
            session.close()

if __name__ == "__main__":
    unittest.main()
