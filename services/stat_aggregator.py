from database import Database
from models.stats import UserStat
from models.achievements import GameEvent
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy import text
import json
import datetime

class StatAggregator:
    """
    Processes GameEvents and updates UserStats using efficient UPSERT operations.
    This avoids UniqueViolation errors in high-concurrency scenarios.
    """
    
    def __init__(self):
        self.db = Database()
        self._batch_cache = {} # Stores (user_id, stat_key) -> {'op': 'inc'|'set', 'value': val}
        
    def process_events(self, events, session=None):
        """
        Process a batch of events and aggregate stats in memory, then flush to DB.
        """
        if not events:
            return
            
        local_session = False
        if not session:
            session = self.db.get_session()
            local_session = True
            
        # Reset local cache for this batch
        self._batch_cache = {}
        
        try:
            # 1. Filter out users that don't exist in 'utente' table
            user_ids = list(set(e.user_id for e in events))
            from models.user import Utente
            existing_user_ids = [r[0] for r in session.query(Utente.id_telegram).filter(Utente.id_telegram.in_(user_ids)).all()]
            
            # 1. Aggregate all events in memory
            for event in events:
                if event.user_id not in existing_user_ids:
                    # Skip events for non-existent users (prevents achievement awards to non-users)
                    event.processed = True
                    continue
                    
                # Re-attach event to current session if needed
                if event not in session:
                    event = session.merge(event)
                self._process_single_event(session, event)
                event.processed = True
            
            # 2. Flush aggregated stats to DB using UPSERT
            self._flush_stats(session)
            
            if local_session:
                session.commit()
            else:
                session.flush()
        except Exception as e:
            print(f"[ERROR] Stat Aggregation failed: {e}")
            if local_session:
                session.rollback()
            raise e
        finally:
            self._batch_cache = {}
            if local_session:
                session.close()

    def _flush_stats(self, session):
        """
        Execute batch UPSERTs for all aggregated stats.
        """
        if not self._batch_cache:
            return

        # Prepare data for bulk execution
        # We need separate logic for 'inc' (increment) and 'set' (overwrite)
        
        for (user_id, stat_key), data in self._batch_cache.items():
            op = data['op']
            value = data['value']
            now = datetime.datetime.now()
            
            stmt = insert(UserStat).values(
                user_id=user_id,
                stat_key=stat_key,
                value=value,
                last_updated=now
            )
            
            if op == 'inc':
                # ON CONFLICT DO UPDATE SET value = user_stat.value + :value
                stmt = stmt.on_conflict_do_update(
                    index_elements=['user_id', 'stat_key'],
                    set_={
                        'value': UserStat.value + stmt.excluded.value,
                        'last_updated': now
                    }
                )
            elif op == 'set':
                # ON CONFLICT DO UPDATE SET value = :value
                stmt = stmt.on_conflict_do_update(
                    index_elements=['user_id', 'stat_key'],
                    set_={
                        'value': stmt.excluded.value, # Overwrite
                        'last_updated': now
                    }
                )
            
            # Execute the statement
            session.execute(stmt)

    def _process_single_event(self, session, event):
        """
        Update stats based on a single event.
        """
        user_id = event.user_id
        event_type = event.event_type
        value = event.value
        context = json.loads(event.context) if event.context else {}
        
        # 1. Update Base Stat (Direct Mapping)
        self._increment_stat(user_id, event_type, value if value > 0 else 1)
        
        # 2. Derived Stats Logic
        if event_type == 'mob_kill':
            self._increment_stat(user_id, 'total_kills', 1)
            
            # Specific Mob Kills
            mob_name = context.get('mob_name')
            if mob_name:
                stat_key = f"kill_{mob_name.lower().replace(' ', '_')}"
                self._increment_stat(user_id, stat_key, 1)
                
                # Android Kills Group
                if mob_name in ['C17', 'C18', 'C19', 'C20']:
                    self._increment_stat(user_id, 'android_kills', 1)

            # High Level Kills
            mob_level = context.get('mob_level', 0)
            player_level = context.get('player_level', 1000)
            if mob_level >= player_level + 10:
                self._increment_stat(user_id, 'high_level_kills', 1)
                
            # Boss Kills
            if context.get('is_boss'):
                self._increment_stat(user_id, 'boss_kills', 1)
                
        elif event_type == 'damage_dealt':
            self._increment_stat(user_id, 'total_damage', value)
            
            # One Shot
            if context.get('is_one_shot'):
                self._increment_stat(user_id, 'one_shots', 1)
                
            # Critical Hits
            if context.get('is_crit'):
                self._increment_stat(user_id, 'critical_hits', 1)
                
        elif event_type == 'heal_given':
            self._increment_stat(user_id, 'total_heals', value)
            
        elif event_type == 'damage_taken':
            self._increment_stat(user_id, 'total_damage_taken', value)
            if context.get('mitigated', 0) > 0:
                self._increment_stat(user_id, 'total_mitigated', context['mitigated'])
                
        elif event_type == 'dungeon_run':
            self._increment_stat(user_id, 'dungeons_completed', 1)
            if context.get('damage_rank') == 1:
                self._increment_stat(user_id, 'dungeon_mvp_damage', 1)
                
        elif event_type == 'chat_exp':
            self._increment_stat(user_id, 'total_chat_exp', value)
            
        elif event_type == 'point_gain':
            self._increment_stat(user_id, 'total_wumpa_earned', value)

        elif event_type == 'level_up':
            self._set_stat(user_id, 'level', value)

        elif event_type == 'item_gain':
            item_name = context.get('item_name', '')
            if "Sfera del Drago" in item_name:
                self._increment_stat(user_id, 'dragon_balls_collected', value)
        
        elif event_type == 'shenron_summoned':
            self._increment_stat(user_id, 'shenron_summons', 1)
            
        elif event_type == 'porunga_summoned':
            self._increment_stat(user_id, 'porunga_summons', 1)

        elif event_type == 'character_unlock':
            char_name = context.get('char_name')
            if char_name:
                stat_key = f"unlock_{char_name.lower().replace(' ', '_')}"
                self._increment_stat(user_id, stat_key, 1)
                self._increment_stat(user_id, 'total_characters_unlocked', 1)

        elif event_type == 'character_equip':
            char_name = context.get('char_name')
            if char_name:
                stat_key = f"use_{char_name.lower().replace(' ', '_')}"
                self._increment_stat(user_id, stat_key, 1)

        # --- MARKET EVENTS ---
        elif event_type == 'ITEM_LISTED':
            self._increment_stat(user_id, 'items_listed', 1)
            
        elif event_type == 'ITEM_SOLD':
            self._increment_stat(user_id, 'items_sold', 1)
            
        elif event_type == 'ITEM_BOUGHT':
            self._increment_stat(user_id, 'items_bought', 1)
            self._increment_stat(user_id, 'total_spent_market', value)
            
        elif event_type == 'MARKET_VIEWED':
            self._increment_stat(user_id, 'market_views', 1)
            
        elif event_type == 'QUICK_SALE':
            self._increment_stat(user_id, 'quick_sales', 1)

        # --- CRAFTING EVENTS ---
        elif event_type == 'RESOURCE_DROP':
            self._increment_stat(user_id, 'resources_collected', value if value > 0 else 1)
            
        elif event_type == 'CRAFTING_COMPLETE':
            self._increment_stat(user_id, 'items_crafted', 1)
            
        elif event_type == 'PROFESSION_LEVELUP':
            self._set_stat(user_id, 'profession_level', value)

    def _increment_stat(self, user_id, stat_key, amount):
        """
        Queue a stat increment in local batch cache.
        """
        key = (user_id, stat_key)
        
        if key in self._batch_cache:
            # Update existing entry
            entry = self._batch_cache[key]
            entry['value'] += amount
            # Note: if op was 'set', it stays 'set' but value increases relative to setting
        else:
            # Create new entry
            self._batch_cache[key] = {'op': 'inc', 'value': amount}

    def _set_stat(self, user_id, stat_key, value):
        """
        Queue a stat overwrite in local batch cache.
        """
        key = (user_id, stat_key)
        self._batch_cache[key] = {'op': 'set', 'value': value}
