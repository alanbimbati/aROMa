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
    
    def log_event(self, event_type, user_id, value=0.0, context=None, session=None):
        """
        Log a game event for achievement tracking
        
        Args:
            event_type: Type of event (mob_kill, damage_dealt, etc.)
            user_id: Telegram ID of user
            value: Primary metric (damage amount, exp gained, etc.)
            context: Dictionary with event-specific context
            session: Optional existing SQLAlchemy session to use
            
        Returns:
            Event ID
        """
        local_session = False
        if session is None:
            session = self.db.get_session()
            local_session = True
            
        try:
            event = GameEvent(
                event_type=event_type,
                user_id=user_id,
                value=value,
                context=json.dumps(context) if context else None,
                timestamp=datetime.datetime.now(),
                processed=False
            )
            
            session.add(event)
            if local_session:
                session.commit()
            else:
                session.flush() # Ensure ID is generated but don't commit yet
            
            return event.id
        except Exception as e:
            if local_session:
                session.rollback()
            print(f"Error logging event: {e}")
            return None
        finally:
            if local_session:
                session.close()
    
    def get_unprocessed_events(self, limit=100):
        """Get events that haven't been processed for achievements"""
        session = self.db.get_session()
        try:
            events = session.query(GameEvent).filter(
                GameEvent.processed == False
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
                event.processed = True
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
