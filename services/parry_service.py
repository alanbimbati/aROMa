"""
Parry Service - Core logic for the advanced parry system

Handles:
- Parry window activation and validation
- Reaction time calculations
- Counterattack timing and multipliers
- Statistics aggregation
- Telemetry logging
- Achievement progress tracking
"""

from database import Database
from sqlalchemy import text
from datetime import datetime, timedelta
from services.event_dispatcher import EventDispatcher
import json


class ParryService:
    """Service for managing parry mechanics and tracking"""
    
    # Configuration constants
    PARRY_WINDOW_MS = 2500  # 2.5 seconds (aligned with tests)
    PERFECT_THRESHOLD_MS = 300  # 0.3 seconds for perfect parry
    COUNTERATTACK_WINDOW_MS = 5000  # 5 seconds for damage bonus
    COUNTERATTACK_MULTIPLIER = 1.5  # Damage bonus within window
    LATE_COUNTER_MULTIPLIER = 1.0  # Normal damage after window
    DAMAGE_NEGATION_STANDARD = 0.75  # 75% damage reduction
    DAMAGE_NEGATION_PERFECT = 1.0  # 100% damage reduction
    
    def __init__(self):
        self.db = Database()
        self.event_dispatcher = EventDispatcher()
    
    def activate_parry(self, user_id, mob_id, session=None):
        """
        Activate parry window for user
        
        Args:
            user_id: Telegram user ID
            mob_id: ID of mob being fought
            session: Optional database session
            
        Returns:
            dict: {
                'success': bool,
                'parry_id': int (if success),
                'window_duration': float (seconds),
                'expires_at': datetime,
                'error': str (if not success)
            }
        """
        local_session = False
        if session is None:
            session = self.db.get_session()
            local_session = True
        
        try:
            # Check for existing active parry
            check_query = text("""
                SELECT id, expires_at FROM parry_states
                WHERE user_id = :uid AND status = 'active' AND expires_at > NOW()
            """)
            
            existing = session.execute(check_query, {"uid": user_id}).fetchone()
            
            if existing:
                if local_session:
                    session.close()
                return {
                    'success': True,
                    'parry_id': existing[0],
                    'window_duration': self.PARRY_WINDOW_MS / 1000,
                    'expires_at': existing[1]
                }
            
            # Create new parry state
            now = datetime.now()
            expires_at = now + timedelta(milliseconds=self.PARRY_WINDOW_MS)
            
            insert_query = text("""
                INSERT INTO parry_states (user_id, mob_id, activated_at, expires_at, status)
                VALUES (:uid, :mid, :activated, :expires, 'active')
                RETURNING id
            """)
            
            result = session.execute(insert_query, {
                "uid": user_id,
                "mid": mob_id,
                "activated": now,
                "expires": expires_at
            })
            
            parry_id = result.scalar()
            
            # Initialize stats first
            self._initialize_stats(user_id, session=session)
            
            # Log telemetry
            self.log_parry_event(user_id, 'PARRY_ATTEMPT', {
                'parry_id': parry_id,
                'mob_id': mob_id,
                'window_duration_ms': self.PARRY_WINDOW_MS
            }, session=session)
            
            # Update stats
            self._increment_stat(user_id, 'total_parry_attempts', session=session)
            
            if local_session:
                session.commit()
                session.close()
            
            return {
                'success': True,
                'parry_id': parry_id,
                'window_duration': self.PARRY_WINDOW_MS / 1000,
                'expires_at': expires_at
            }
            
        except Exception as e:
            if local_session:
                session.rollback()
                session.close()
            return {
                'success': False,
                'error': f'Errore attivazione parry: {str(e)}'
            }
    
    def check_parry_window(self, user_id, session=None):
        """
        Check if user has an active parry window
        
        Returns:
            dict or None: Parry state if active, None otherwise
        """
        local_session = False
        if not session:
            session = self.db.get_session()
            local_session = True
        
        try:
            query = text("""
                SELECT id, mob_id, activated_at, expires_at
                FROM parry_states
                WHERE user_id = :uid AND status = 'active' AND expires_at > NOW()
                ORDER BY created_at DESC
                LIMIT 1
            """)
            
            result = session.execute(query, {"uid": user_id}).fetchone()
            
            if local_session:
                session.close()
            
            if result:
                return {
                    'parry_id': result[0],
                    'mob_id': result[1],
                    'activated_at': result[2],
                    'expires_at': result[3]
                }
            
            return None
            
        except Exception as e:
            session.close()
            print(f"[ParryService] Error checking parry window: {e}")
            return None

    def get_active_counter_window(self, user_id):
        """Check for a successful parry that allows a counterattack"""
        session = self.db.get_session()
        try:
            # Look for success/perfect parries that haven't been used for a counter yet
            query = text("""
                SELECT id, activated_at, status
                FROM parry_states
                WHERE user_id = :uid AND status IN ('success', 'perfect')
                AND counterattack_at IS NULL
                AND activated_at > NOW() - INTERVAL '10 seconds'
                ORDER BY created_at DESC
                LIMIT 1
            """)
            result = session.execute(query, {"uid": user_id}).fetchone()
            session.close()
            if result:
                return {
                    'parry_id': result[0],
                    'activated_at': result[1],
                    'status': result[2]
                }
            return None
        except Exception as e:
            session.close()
            print(f"[ParryService] Error getting counter window: {e}")
            return None
    
    def process_enemy_attack(self, user_id, mob_id, attack_damage, attack_time=None, session=None):
        """
        Process enemy attack during parry window
        
        Args:
            user_id: Telegram user ID
            mob_id: ID of attacking mob
            attack_damage: Base damage of attack
            attack_time: Timestamp of attack (default: now)
            session: Optional database session
            
        Returns:
            dict: {
                'success': bool,
                'parry_active': bool,
                'perfect': bool (if success),
                'reaction_time': int (ms),
                'damage_taken': int,
                'damage_avoided': int,
                'counterattack': bool,
                'multiplier': float,
                'cooldown_reset': bool
            }
        """
        if attack_time is None:
            attack_time = datetime.now()
        
        # Check for active parry
        parry_state = self.check_parry_window(user_id, session=session)
        
        if not parry_state:
            return {
                'success': False,
                'parry_active': False
            }
        
        # Calculate reaction time
        reaction_ms = self.calculate_reaction_time(
            parry_state['activated_at'],
            attack_time
        )
        
        # Determine parry type
        is_perfect = reaction_ms <= self.PERFECT_THRESHOLD_MS
        
        # Calculate damage reduction
        if is_perfect:
            damage_taken = 0
            damage_avoided = attack_damage
            negation_pct = self.DAMAGE_NEGATION_PERFECT
        else:
            damage_taken = int(attack_damage * (1 - self.DAMAGE_NEGATION_STANDARD))
            damage_avoided = attack_damage - damage_taken
            negation_pct = self.DAMAGE_NEGATION_STANDARD
        
        # Update parry state
        local_session = False
        if not session:
            session = self.db.get_session()
            local_session = True
            
        try:
            update_query = text("""
                UPDATE parry_states
                SET status = :status, reaction_time_ms = :reaction
                WHERE id = :pid
            """)
            
            session.execute(update_query, {
                "pid": parry_state['parry_id'],
                "status": 'perfect' if is_perfect else 'success',
                "reaction": reaction_ms
            })
            
            # Log telemetry
            self.log_parry_event(user_id, 'PARRY_PERFECT' if is_perfect else 'PARRY_SUCCESS', {
                'parry_id': parry_state['parry_id'],
                'mob_id': mob_id,
                'reaction_time_ms': reaction_ms,
                'damage_avoided': damage_avoided,
                'damage_taken': damage_taken
            }, session=session)
            
            # Update stats
            self.update_parry_stats(user_id, {
                'perfect': is_perfect,
                'reaction_time_ms': reaction_ms,
                'damage_avoided': damage_avoided
            }, session=session)
            
            if local_session:
                session.commit()
                session.close()
        except Exception as e:
            if local_session:
                session.rollback()
                session.close()
            print(f"[ParryService] Error updating parry status/stats: {e}")
        
        return {
            'success': True,
            'parry_active': True,
            'perfect': is_perfect,
            'reaction_time': reaction_ms,
            'damage_taken': damage_taken,
            'damage_avoided': damage_avoided,
            'counterattack': True,
            'multiplier': 1.5 if is_perfect else 1.2,
            'cooldown_reset': True,
            'parry_id': parry_state['parry_id'],
            'parry_time': parry_state['activated_at']
        }
        
    def update_parry_stats(self, user_id, event_data, session=None):
        """
        Public method to update parry statistics.
        Matches test expectations.
        """
        is_perfect = event_data.get('perfect', False)
        reaction_ms = event_data.get('reaction_time_ms', 0)
        damage_avoided = event_data.get('damage_avoided', 0)
        
        self._update_parry_success_stats(user_id, is_perfect, reaction_ms, damage_avoided, session=session)
    
    def calculate_counterattack_multiplier(self, parry_time, counter_time=None):
        """
        Calculate damage multiplier based on counterattack timing
        
        Args:
            parry_time: Timestamp when parry succeeded
            counter_time: Timestamp of counterattack (default: now)
            
        Returns:
            dict: {
                'multiplier': float (1.5x within window, 1.0x after),
                'in_window': bool,
                'counter_time_ms': int
            }
        """
        if counter_time is None:
            counter_time = datetime.now()
        
        # Calculate time since parry
        counter_ms = int((counter_time - parry_time).total_seconds() * 1000)
        
        # Check if within counterattack window
        in_window = counter_ms <= self.COUNTERATTACK_WINDOW_MS
        
        multiplier = self.COUNTERATTACK_MULTIPLIER if in_window else self.LATE_COUNTER_MULTIPLIER
        
        return {
            'multiplier': multiplier,
            'in_window': in_window,
            'counter_time_ms': counter_ms
        }
    
    def log_counterattack(self, user_id, parry_id, counter_time, damage_dealt):
        """
        Log counterattack event and update statistics
        
        Args:
            user_id: Telegram user ID
            parry_id: ID of parry state
            counter_time: Timestamp of counterattack
            damage_dealt: Damage dealt by counterattack
        """
        session = self.db.get_session()
        
        try:
            # Get parry activation time
            query = text("""
                SELECT activated_at FROM parry_states WHERE id = :pid
            """)
            result = session.execute(query, {"pid": parry_id}).fetchone()
            
            if not result:
                session.close()
                return
            
            parry_time = result[0]
            counter_ms = int((counter_time - parry_time).total_seconds() * 1000)
            in_window = counter_ms <= self.COUNTERATTACK_WINDOW_MS
            
            # Update parry state
            update_query = text("""
                UPDATE parry_states
                SET counterattack_at = :counter_time
                WHERE id = :pid
            """)
            session.execute(update_query, {"pid": parry_id, "counter_time": counter_time})
            session.commit()
            
            # Log telemetry
            event_type = 'COUNTERATTACK_BONUS' if in_window else 'COUNTERATTACK_LATE'
            self.log_parry_event(user_id, event_type, {
                'parry_id': parry_id,
                'counter_time_ms': counter_ms,
                'damage_dealt': damage_dealt,
                'in_window': in_window
            }, session=None)
            
            # Update stats
            if in_window:
                self._increment_stat(user_id, 'total_counters_in_window', session=None)
            else:
                self._increment_stat(user_id, 'total_counters_late', session=None)
            
            self._add_to_stat(user_id, 'total_counterattack_damage', damage_dealt, session=None)
            
            session.close()
            
        except Exception as e:
            session.rollback()
            session.close()
            print(f"[ParryService] Error logging counterattack: {e}")
    
    def calculate_reaction_time(self, parry_time, attack_time):
        """
        Calculate reaction time in milliseconds
        
        Args:
            parry_time: Timestamp of parry activation
            attack_time: Timestamp of enemy attack
            
        Returns:
            int: Reaction time in milliseconds
        """
        delta = (attack_time - parry_time).total_seconds() * 1000
        return int(delta)
    
    def expire_parry_window(self, user_id):
        """
        Expire active parry windows that have timed out
        
        Called periodically or when checking for active parries
        """
        session = self.db.get_session()
        
        try:
            query = text("""
                UPDATE parry_states
                SET status = 'failed'
                WHERE user_id = :uid AND status = 'active' AND expires_at <= NOW()
                RETURNING id
            """)
            
            result = session.execute(query, {"uid": user_id})
            expired_ids = [row[0] for row in result.fetchall()]
            session.commit()
            
            # Update stats for failed parries
            if expired_ids:
                self._increment_stat(user_id, 'total_parry_failed', count=len(expired_ids), session=None)
                self._reset_streak(user_id, session=session) # Pass session here
                
                # Log telemetry
                for parry_id in expired_ids:
                    self.log_parry_event(user_id, 'PARRY_FAILED', {
                        'parry_id': parry_id,
                        'reason': 'window_expired'
                    }, session=None)
            
            session.close()
            return len(expired_ids)
            
        except Exception as e:
            session.rollback()
            session.close()
            print(f"[ParryService] Error expiring parry windows: {e}")
            return 0
    
    def get_user_parry_stats(self, user_id):
        """Get aggregated parry statistics for user"""
        session = self.db.get_session()
        
        try:
            query = text("""
                SELECT * FROM parry_stats WHERE user_id = :uid
            """)
            
            result = session.execute(query, {"uid": user_id}).fetchone()
            
            if not result:
                # Initialize stats if not exist
                self._initialize_stats(user_id, session=session) # Pass session here
                session.commit() # Commit the initialization
                session.close() # Close session after commit
                return self.get_user_parry_stats(user_id) # Re-fetch stats
            
            session.close() # Close session if result was found
            
            # Convert to dict
            columns = [
                'user_id', 'total_parry_attempts', 'total_parry_success', 'total_parry_perfect',
                'total_parry_failed', 'max_parry_streak', 'current_parry_streak',
                'max_perfect_streak', 'current_perfect_streak', 'boss_parries',
                'perfect_boss_parries', 'total_damage_avoided', 'total_counterattack_damage',
                'total_counters_in_window', 'total_counters_late', 'average_reaction_time_ms',
                'best_reaction_time_ms', 'average_counter_time_ms', 'flawless_victories',
                'speed_victories', 'last_parry_at', 'updated_at'
            ]
            
            stats = dict(zip(columns, result))
            return stats
            
        except Exception as e:
            session.close()
            print(f"[ParryService] Error getting stats: {e}")
            return None
    
    def log_parry_event(self, user_id, event_type, data, session=None):
        """Log event to combat_telemetry table"""
        local_session = False
        if session is None:
            session = self.db.get_session()
            local_session = True
        
        try:
            query = text("""
                INSERT INTO combat_telemetry (
                    user_id, event_type, mob_id, reaction_time_ms,
                    counterattack_time_ms, damage_dealt, damage_avoided,
                    metadata, timestamp
                )
                VALUES (
                    :uid, :event, :mob, :reaction, :counter_time,
                    :damage_dealt, :damage_avoided, :metadata, NOW()
                )
            """)
            
            session.execute(query, {
                "uid": user_id,
                "event": event_type,
                "mob": data.get('mob_id'),
                "reaction": data.get('reaction_time_ms'),
                "counter_time": data.get('counter_time_ms'),
                "damage_dealt": data.get('damage_dealt', 0),
                "damage_avoided": data.get('damage_avoided', 0),
                "metadata": json.dumps(data)
            })
            
            if local_session:
                session.commit()
                session.close()
                
        except Exception as e:
            if local_session:
                session.rollback()
                session.close()
            print(f"[ParryService] Error logging event: {e}")
    
    # Private helper methods
    
    def _initialize_stats(self, user_id, session=None):
        """Initialize parry stats for new user"""
        local_session = False
        if session is None:
            session = self.db.get_session()
            local_session = True
        
        try:
            query = text("""
                INSERT INTO parry_stats (user_id)
                VALUES (:uid)
                ON CONFLICT (user_id) DO NOTHING
            """)
            session.execute(query, {"uid": user_id})
            
            if local_session:
                session.commit()
                session.close()
        except Exception as e:
            if local_session:
                session.rollback()
                session.close()
            print(f"[ParryService] Error initializing stats: {e}")
    
    def _increment_stat(self, user_id, stat_name, count=1, session=None):
        """Increment a stat counter"""
        local_session = False
        if session is None:
            session = self.db.get_session()
            local_session = True
        
        try:
            self._initialize_stats(user_id, session=session)
            
            query = text(f"""
                UPDATE parry_stats
                SET {stat_name} = {stat_name} + :count, updated_at = NOW()
                WHERE user_id = :uid
            """)
            session.execute(query, {"uid": user_id, "count": count})
            
            if local_session:
                session.commit()
                session.close()
        except Exception as e:
            if local_session:
                session.rollback()
                session.close()
            print(f"[ParryService] Error incrementing stat: {e}")
    
    def _add_to_stat(self, user_id, stat_name, value, session=None):
        """Add value to a stat"""
        self._increment_stat(user_id, stat_name, count=value, session=session)
    
    def _update_parry_success_stats(self, user_id, is_perfect, reaction_ms, damage_avoided, session=None):
        """Update stats after successful parry"""
        local_session = False
        if session is None:
            session = self.db.get_session()
            local_session = True
        
        try:
            # Increment success counters
            self._increment_stat(user_id, 'total_parry_success', session=session)
            if is_perfect:
                self._increment_stat(user_id, 'total_parry_perfect', session=session)
            
            # Update damage avoided
            self._add_to_stat(user_id, 'total_damage_avoided', damage_avoided, session=session)
            
            # Update streaks
            query = text("""
                UPDATE parry_stats
                SET 
                    current_parry_streak = current_parry_streak + 1,
                    max_parry_streak = GREATEST(max_parry_streak, current_parry_streak + 1),
                    current_perfect_streak = CASE WHEN :perfect THEN current_perfect_streak + 1 ELSE 0 END,
                    max_perfect_streak = CASE WHEN :perfect THEN GREATEST(max_perfect_streak, current_perfect_streak + 1) ELSE max_perfect_streak END,
                    best_reaction_time_ms = CASE 
                        WHEN best_reaction_time_ms IS NULL OR :reaction < best_reaction_time_ms 
                        THEN :reaction 
                        ELSE best_reaction_time_ms 
                    END,
                    last_parry_at = NOW(),
                    updated_at = NOW()
                WHERE user_id = :uid
            """)
            
            session.execute(query, {
                "uid": user_id,
                "perfect": is_perfect,
                "reaction": reaction_ms
            })
            
            if local_session:
                session.commit()
                session.close()
            
        except Exception as e:
            if local_session:
                session.rollback()
                session.close()
            print(f"[ParryService] Error updating success stats: {e}")
            
    def expire_parry_window(self, parry_id, user_id):
        """Handle expiration of a parry window that was never triggered"""
        session = self.db.get_session()
        try:
            # Mark as failed
            query = text("""
                UPDATE parry_states 
                SET status = 'failed' 
                WHERE id = :pid AND status = 'active'
            """)
            result = session.execute(query, {"pid": parry_id})
            
            if result.rowcount > 0:
                print(f"[ParryService] Parry {parry_id} expired for user {user_id}")
                # Reset streak
                self._reset_streak(user_id, session=session)
            
            session.commit()
            session.close()
        except Exception as e:
            session.rollback()
            session.close()
            print(f"[ParryService] Error expiring parry: {e}")

    def _reset_streak(self, user_id, session=None):
        """Reset current streaks on failed parry"""
        local_session = False
        if session is None:
            session = self.db.get_session()
            local_session = True
        
        try:
            query = text("""
                UPDATE parry_stats
                SET current_parry_streak = 0, current_perfect_streak = 0, updated_at = NOW()
                WHERE user_id = :uid
            """)
            session.execute(query, {"uid": user_id})
            
            if local_session:
                session.commit()
                session.close()
        except Exception as e:
            if local_session:
                session.rollback()
                session.close()
            print(f"[ParryService] Error resetting streak: {e}")
