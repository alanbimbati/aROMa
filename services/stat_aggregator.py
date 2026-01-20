from database import Database
from models.stats import UserStat
from models.achievements import GameEvent
import json
import datetime

class StatAggregator:
    """
    Processes GameEvents and updates UserStats.
    This is the core of the Data-Driven Achievement System.
    """
    
    def __init__(self):
        self.db = Database()
        
    def process_events(self, events):
        """
        Process a batch of events and update stats.
        """
        if not events:
            return
            
        session = self.db.get_session()
        try:
            for event in events:
                # Re-attach event to current session
                event = session.merge(event)
                self._process_single_event(session, event)
                event.processed = True
            
            session.commit()
        except Exception as e:
            print(f"[ERROR] Stat Aggregation failed: {e}")
            session.rollback()
        finally:
            session.close()

    def _process_single_event(self, session, event):
        """
        Update stats based on a single event.
        """
        user_id = event.user_id
        event_type = event.event_type
        value = event.value
        context = json.loads(event.context) if event.context else {}
        
        # 1. Update Base Stat (Direct Mapping)
        # e.g., 'mob_kill' -> 'total_mob_kill' (or just 'mob_kill')
        # We use the event_type as the base stat key usually
        self._increment_stat(session, user_id, event_type, value if value > 0 else 1)
        
        # 2. Derived Stats Logic
        if event_type == 'mob_kill':
            self._increment_stat(session, user_id, 'total_kills', 1)
            
            # Specific Mob Kills
            mob_name = context.get('mob_name')
            if mob_name:
                # Normalize name for stat key (e.g., "Raditz" -> "kill_raditz")
                stat_key = f"kill_{mob_name.lower().replace(' ', '_')}"
                self._increment_stat(session, user_id, stat_key, 1)
                
                # Android Kills Group
                if mob_name in ['C17', 'C18', 'C19', 'C20']:
                    self._increment_stat(session, user_id, 'android_kills', 1)

            # High Level Kills
            mob_level = context.get('mob_level', 0)
            player_level = context.get('player_level', 1000) # Default high to avoid false positives
            if mob_level >= player_level + 10:
                self._increment_stat(session, user_id, 'high_level_kills', 1)
                
            # Boss Kills
            if context.get('is_boss'):
                self._increment_stat(session, user_id, 'boss_kills', 1)
                
        elif event_type == 'damage_dealt':
            self._increment_stat(session, user_id, 'total_damage', value)
            
            # One Shot
            if context.get('is_one_shot'):
                self._increment_stat(session, user_id, 'one_shots', 1)
                
            # Critical Hits
            if context.get('is_crit'):
                self._increment_stat(session, user_id, 'critical_hits', 1)
                
        elif event_type == 'heal_given':
            self._increment_stat(session, user_id, 'total_heals', value)
            
        elif event_type == 'damage_taken':
            self._increment_stat(session, user_id, 'total_damage_taken', value)
            if context.get('mitigated', 0) > 0:
                self._increment_stat(session, user_id, 'total_mitigated', context['mitigated'])
                
        elif event_type == 'dungeon_run':
            self._increment_stat(session, user_id, 'dungeons_completed', 1)
            if context.get('damage_rank') == 1:
                self._increment_stat(session, user_id, 'dungeon_mvp_damage', 1)
                
        elif event_type == 'chat_exp':
            self._increment_stat(session, user_id, 'total_chat_exp', value)
            
        elif event_type == 'point_gain':
            self._increment_stat(session, user_id, 'total_wumpa_earned', value)

        elif event_type == 'item_gain':
            item_name = context.get('item_name', '')
            if "Sfera del Drago" in item_name:
                self._increment_stat(session, user_id, 'dragon_balls_collected', value)
        
        elif event_type == 'shenron_summoned':
            self._increment_stat(session, user_id, 'shenron_summons', 1)
            
        elif event_type == 'porunga_summoned':
            self._increment_stat(session, user_id, 'porunga_summons', 1)

        elif event_type == 'character_unlock':
            char_name = context.get('char_name')
            if char_name:
                stat_key = f"unlock_{char_name.lower().replace(' ', '_')}"
                self._increment_stat(session, user_id, stat_key, 1)
                self._increment_stat(session, user_id, 'total_characters_unlocked', 1)

        elif event_type == 'character_equip':
            char_name = context.get('char_name')
            if char_name:
                stat_key = f"use_{char_name.lower().replace(' ', '_')}"
                self._increment_stat(session, user_id, stat_key, 1)

    def _increment_stat(self, session, user_id, stat_key, amount):
        """
        Helper to safely increment a UserStat.
        """
        stat = session.query(UserStat).filter_by(user_id=user_id, stat_key=stat_key).first()
        if stat:
            stat.value += amount
        else:
            stat = UserStat(user_id=user_id, stat_key=stat_key, value=amount)
            session.add(stat)
