
import unittest
from unittest.mock import MagicMock, patch
from services.cultivation_service import CultivationService
from services.alchemy_service import AlchemyService
from services.achievement_tracker import AchievementTracker
from models.achievements import UserAchievement
from database import Database
from sqlalchemy import text


class TestProfessionAchievements(unittest.TestCase):
    
    def setUp(self):
        self.db = Database()
        self.session = self.db.get_session()
        
        # Ensure schema is up to date (patch for missing migrations in test env)
        try:
            self.session.execute(text("ALTER TABLE utente ADD COLUMN profumino_until TIMESTAMP"))
            self.session.commit()
        except Exception:
            self.session.rollback()
            
        # Clean up previous test data
        self.user_id = 987654321
        self.session.execute(text("DELETE FROM user_achievement WHERE user_id = :uid"), {"uid": self.user_id})
        self.session.execute(text("DELETE FROM user_stat WHERE user_id = :uid"), {"uid": self.user_id})
        self.session.execute(text("DELETE FROM game_event WHERE user_id = :uid"), {"uid": self.user_id})
        self.session.execute(text("DELETE FROM utente WHERE \"id_Telegram\" = :uid"), {"uid": self.user_id})
        
        self.session.execute(text("INSERT INTO utente (\"id_Telegram\", nome, livello) VALUES (:uid, 'TestUser', 1)"), {"uid": self.user_id})
        self.session.commit()
        
        self.cultivation_service = CultivationService()
        self.alchemy_service = AlchemyService()
        self.achievement_tracker = AchievementTracker()
        
        # We assume achievements already exist in the target DB
        # Re-open session to ensure clean state
        self.session.close()
        self.session = self.db.get_session()

    def tearDown(self):
        self.session.execute(text("DELETE FROM user_achievement WHERE user_id = :uid"), {"uid": self.user_id})
        self.session.execute(text("DELETE FROM user_stat WHERE user_id = :uid"), {"uid": self.user_id})
        self.session.execute(text("DELETE FROM game_event WHERE user_id = :uid"), {"uid": self.user_id})
        self.session.execute(text("DELETE FROM utente WHERE \"id_Telegram\" = :uid"), {"uid": self.user_id})
        self.session.commit()
        self.session.close()

    def test_green_thumb_achievement(self):
        # Trigger harvests
        for _ in range(10):
            # We mock the internal event logging or call the method?
            # Calling the method requires setup (seeds, slots). 
            # It's easier to simulate the event via EventDispatcher directly for this unit test if we want to test the Tracker,
            # OR we test the Service emits the event.
            
            # Let's test the components integration: Service emits -> Dispatcher logs -> Tracker processes.
            
            # Since running the full service method is complex (needs DB state), 
            # let's just use the EventDispatcher to log the event manually, 
            # mimicking what the service does. This verifies the Achievement Logic.
            
            self.cultivation_service.event_dispatcher.log_event(
                event_type="garden_harvest",
                user_id=self.user_id,
                value=1,
                context={"seed_type": "Semi di Wumpa"},
                session=self.session
            )
        import sys
        
        # Verify user exists via SQL
        res = self.session.execute(text("SELECT \"id_Telegram\" FROM utente WHERE \"id_Telegram\" = :uid"), {"uid": self.user_id})
        rows = res.fetchall()
        if not rows:
            self.fail(f"[TEST FAIL] User NOT found via SQL. ID: {self.user_id}")

        # Verify user exists via ORM
        from models.user import Utente
        u = self.session.query(Utente).filter_by(id_telegram=self.user_id).first()
        if not u:
            self.fail(f"[TEST FAIL] User NOT found via ORM. SQL found: {rows}")
        
        # Process events
        # Process events
        print("[TEST DEBUG] Processing events...")
        self.achievement_tracker.process_pending_events(limit=100, session=self.session)
        self.session.commit() # Ensure everything is persisted
        
        # Check Stats
        from models.stats import UserStat
        stat = self.session.query(UserStat).filter_by(user_id=self.user_id, stat_key='garden_plants_harvested').first()
        print(f"[TEST DEBUG] Stat garden_plants_harvested: {stat.value if stat else 'None'}")
        
        # Check achievement
        ua = self.session.query(UserAchievement).filter_by(
            user_id=self.user_id, achievement_key='green_thumb'
        ).first()
        
        self.assertIsNotNone(ua)
        self.assertEqual(ua.current_tier, 'bronze')
        self.assertEqual(ua.progress_value, 10)

    def test_master_alchemist_achievement(self):
        # Trigger alchemy brews
        self.alchemy_service.db = self.db # Ensure sharing same DB instance logic if needed
        # Just use dispatcher
        from services.event_dispatcher import EventDispatcher
        dispatcher = EventDispatcher()
        
        for _ in range(10):
            dispatcher.log_event(
                event_type="alchemy_brew",
                user_id=self.user_id,
                value=1,
                context={"potion_name": "Pozione Salute Minore"},
                session=self.session
            )
            
        self.achievement_tracker.process_pending_events(limit=100, session=self.session)
        self.session.commit()
        
        ua = self.session.query(UserAchievement).filter_by(
            user_id=self.user_id, achievement_key='master_alchemist'
        ).first()
        
        self.assertIsNotNone(ua)
        self.assertEqual(ua.current_tier, 'bronze')
        self.assertEqual(ua.progress_value, 10)
        
    def test_botanist_achievement(self):
        dispatcher = self.cultivation_service.event_dispatcher
        
        # Discovery Green
        dispatcher.log_event(event_type="herb_discovery", user_id=self.user_id, value=1, context={"herb_name": "Erba Verde"}, session=self.session)
        self.achievement_tracker.process_pending_events(session=self.session)
        
        # Discovery Blue
        dispatcher.log_event(event_type="herb_discovery", user_id=self.user_id, value=1, context={"herb_name": "Erba Blu"}, session=self.session)
        self.achievement_tracker.process_pending_events(session=self.session)
        self.session.commit()
        
        # Check - should not be unlocked yet
        ua = self.session.query(UserAchievement).filter_by(user_id=self.user_id, achievement_key='botanist').first()
        if ua:
            self.assertIsNone(ua.current_tier)
        
        # Discovery Yellow
        dispatcher.log_event(event_type="herb_discovery", user_id=self.user_id, value=1, context={"herb_name": "Erba Gialla"}, session=self.session)
        self.achievement_tracker.process_pending_events(session=self.session)
        self.session.commit()
        
        # Check unlock
        ua = self.session.query(UserAchievement).filter_by(user_id=self.user_id, achievement_key='botanist').first()
        
        # Debug
        from models.stats import UserStat
        stats = self.session.query(UserStat).filter(UserStat.user_id == self.user_id, UserStat.stat_key.like('discovery_%')).all()
        print(f"[TEST DEBUG] Botanist stats: {[s.stat_key for s in stats]}")
        
        self.assertIsNotNone(ua)
        if ua.current_tier != 'gold':
            count = len(stats)
            stat_keys = [s.stat_key for s in stats]
            self.fail(f"Expected Gold, got {ua.current_tier}. Stat Count: {count}. Keys: {stat_keys}. UA Progress: {ua.progress_value}")
        self.assertEqual(ua.current_tier, 'gold')

if __name__ == '__main__':
    unittest.main()
