"""
Weekly Event Manager - Manages rotating weekly events with multipliers.
"""

import datetime
import json

class WeeklyEventManager:
    """Manages rotating weekly events"""
    
    EVENTS = {
        'double_exp': {
            'name': 'Settimana dell\'Esperienza',
            'description': 'Tutti i mostri danno EXP doppia!',
            'duration_days': 7,
            'multipliers': {'exp': 2.0}
        },
        'rare_spawns': {
            'name': 'Invasione Rara',
            'description': 'Mostri rari appaiono più frequentemente!',
            'duration_days': 7,
            'effects': {'rare_spawn_rate': 0.3}
        },
        'boss_rush': {
            'name': 'Boss Rush',
            'description': 'Un boss appare ogni 2 ore!',
            'duration_days': 3,
            'effects': {'boss_spawn_interval': 7200}
        },
        'loot_bonanza': {
            'name': 'Pioggia di Loot',
            'description': 'Drop rate aumentato del 50%!',
            'duration_days': 7,
            'multipliers': {'loot_rate': 1.5}
        }
    }
    
    # Simple in-memory active event (in production, store in database)
    _active_event = None
    _event_end_time = None
    
    @classmethod
    def start_event(cls, event_key):
        """
        Start a weekly event
        
        Args:
            event_key: Key of event to start
            
        Returns:
            Boolean success
        """
        event_config = cls.EVENTS.get(event_key)
        if not event_config:
            return False
        
        cls._active_event = event_key
        cls._event_end_time = datetime.datetime.now() + datetime.timedelta(days=event_config['duration_days'])
        
        return True
    
    @classmethod
    def get_active_event(cls):
        """Get currently active event"""
        if not cls._active_event or not cls._event_end_time:
            return None
        
        if datetime.datetime.now() > cls._event_end_time:
            cls._active_event = None
            cls._event_end_time = None
            return None
        
        return {
            'key': cls._active_event,
            'config': cls.EVENTS[cls._active_event],
            'end_time': cls._event_end_time
        }
    
    @classmethod
    def apply_multiplier(cls, base_value, multiplier_type):
        """
        Apply event multipliers to rewards
        
        Args:
            base_value: Base value to multiply
            multiplier_type: Type of multiplier (exp, loot_rate, etc.)
            
        Returns:
            Modified value
        """
        event = cls.get_active_event()
        if not event:
            return base_value
        
        multipliers = event['config'].get('multipliers', {})
        if multiplier_type in multipliers:
            return int(base_value * multipliers[multiplier_type])
        
        return base_value
