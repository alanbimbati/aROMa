import unittest
from unittest.mock import patch, MagicMock
from database import Database
from models.user import Utente
from models.dungeon import Dungeon, DungeonParticipant
from services.dungeon_service import DungeonService
import datetime
import json

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

    @patch('services.dungeon_service.datetime')
    def test_schedule_creation(self, mock_datetime):
        """Test that a dungeon is scheduled if none exists today"""
        # Set time to 10:00 AM
        fixed_now = datetime.datetime(2025, 1, 1, 10, 0, 0)
        mock_datetime.datetime.now.return_value = fixed_now
        mock_datetime.timedelta = datetime.timedelta # Keep real timedelta
        
        # Mock random so we know the scheduled time
        with patch('random.randint', side_effect=[12, 0, 30]): # Hour 12, Min 0, Delay 30
            self.dungeon_service.check_daily_dungeon_trigger(self.test_chat_id)
            
        # Verify DB
        session = self.db.get_session()
        dungeon = session.query(Dungeon).filter_by(chat_id=self.test_chat_id).first()
        self.assertIsNotNone(dungeon)
        self.assertEqual(dungeon.status, "registration")
        self.assertFalse(dungeon.is_hype_active)
        # Expected time: 12:00
        expected_time = datetime.datetime(2025, 1, 1, 12, 0, 0)
        self.assertEqual(dungeon.scheduled_for, expected_time)
        session.close()

    @patch('services.dungeon_service.datetime')
    def test_hype_trigger(self, mock_datetime):
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
        mock_datetime.datetime.now.return_value = fixed_now
        mock_datetime.timedelta = datetime.timedelta

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

    @patch('services.dungeon_service.datetime')
    def test_auto_start_after_hype(self, mock_datetime):
        """Test that dungeon starts and users auto-join after hype"""
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
        session.close()
        
        # Set time to 12:06 (Hype duration is 5 mins)
        fixed_now = datetime.datetime(2025, 1, 1, 12, 6, 0)
        mock_datetime.datetime.now.return_value = fixed_now
        mock_datetime.timedelta = datetime.timedelta 
        
        # Need to patch spawn_step to avoid implicit database calls needing real mob data
        # or we verify mob spawning separately.
        # But we want to test auto-join count.
        # Let's mock spawn_step.
        
        with patch.object(self.dungeon_service, 'spawn_step', return_value=([], [])) as mock_spawn:
            result = self.dungeon_service.check_daily_dungeon_trigger(self.test_chat_id)
            
            self.assertIsInstance(result, dict)
            self.assertEqual(result['type'], "DUNGEON_STARTED")
            # We created 2 test users (901, 902), plus potentially others in DB?
            # get_session().query(Utente).all() returns ALL users.
            # Tests run on test DB which should be clean or have only our users.
            # But test_dungeon_logic might have left users if not cleaned up properly?
            # Our tearDown/setUp cleans up.
            # But duplicate users with same ID? 'id_telegram' is primary key usually? 
            # Check models/user.py? Usually id is PK, id_telegram is Unique.
            
            # Since we cleared 901/902, and added them, we expect at least 2.
            # But query(Utente).all() might return more from other tests if DB not cleared.
            # We check that >= 2
            self.assertTrue(result['participant_count'] >= 2)
            
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
