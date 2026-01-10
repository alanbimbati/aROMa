"""
Event Dispatcher Service - Centralized event logging and dispatching for achievement tracking.
"""

from database import Database
from models.achievements import GameEvent
import datetime
import json

class EventDispatcher:
    """Centralized event logging and dispatching"""
    
    def __init__(self):
        self.db = Database()
    
    def log_event(self, event_type, user_id, event_data, mob_id=None, combat_id=None):
        """
        Log a game event for achievement tracking
        
        Args:
            event_type: Type of event (mob_kill, damage_dealt, critical_hit, etc.)
            user_id: Telegram ID of user
            event_data: Dictionary with event-specific data
            mob_id: Optional mob ID
            combat_id: Optional combat ID
            
        Returns:
            Event ID
        """
        session = self.db.get_session()
        try:
            event = GameEvent(
                event_type=event_type,
                user_id=user_id,
                event_data=json.dumps(event_data),
                mob_id=mob_id,
                combat_id=combat_id,
                timestamp=datetime.datetime.now(),
                processed_for_achievements=False
            )
            
            session.add(event)
            session.commit()
            
            return event.id
        except Exception as e:
            session.rollback()
            print(f"Error logging event: {e}")
            return None
        finally:
            session.close()
    
    def get_unprocessed_events(self, limit=100):
        """Get events that haven't been processed for achievements"""
        session = self.db.get_session()
        try:
            events = session.query(GameEvent).filter(
                GameEvent.processed_for_achievements == False
            ).limit(limit).all()
            return events
        finally:
            session.close()
    
    def mark_processed(self, event_id):
        """Mark event as processed"""
        session = self.db.get_session()
        try:
            event = session.query(GameEvent).filter(GameEvent.id == event_id).first()
            if event:
                event.processed_for_achievements = True
                session.commit()
                return True
            return False
        except Exception as e:
            session.rollback()
            print(f"Error marking event as processed: {e}")
            return False
        finally:
            session.close()
    
    def get_user_events(self, user_id, event_type=None, limit=50):
        """Get events for a specific user"""
        session = self.db.get_session()
        try:
            query = session.query(GameEvent).filter(GameEvent.user_id == user_id)
            
            if event_type:
                query = query.filter(GameEvent.event_type == event_type)
            
            events = query.order_by(GameEvent.timestamp.desc()).limit(limit).all()
            return events
        finally:
            session.close()
    
    def get_event_count(self, user_id, event_type):
        """Get count of specific event type for user"""
        session = self.db.get_session()
        try:
            count = session.query(GameEvent).filter(
                GameEvent.user_id == user_id,
                GameEvent.event_type == event_type
            ).count()
            return count
        finally:
            session.close()
