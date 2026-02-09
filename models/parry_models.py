"""
SQLAlchemy ORM Models for Parry System

Defines database models for:
- ParryState: Active parry window tracking
- CombatTelemetry: Event logging for analytics
- ParryStats: Aggregated user statistics
"""

from sqlalchemy import Column, Integer, BigInteger, String, Boolean, Float, TIMESTAMP, JSON, ForeignKey
from sqlalchemy.sql import func
from database import Base


class ParryState(Base):
    """
    Tracks active parry windows and their outcomes
    
    A new record is created when a user activates defend.
    Status is updated when enemy attacks or window expires.
    """
    __tablename__ = 'parry_states'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(BigInteger, nullable=False, index=True)
    mob_id = Column(Integer)
    activated_at = Column(TIMESTAMP, nullable=False, server_default=func.now())
    expires_at = Column(TIMESTAMP, nullable=False)
    status = Column(String(20), default='active')  # active, success, perfect, failed, cancelled
    reaction_time_ms = Column(Integer)  # Time between parry activation and enemy attack
    counterattack_at = Column(TIMESTAMP)  # When user counterattacked (if any)
    created_at = Column(TIMESTAMP, server_default=func.now())


class CombatTelemetry(Base):
    """
    Logs all combat events for analytics and achievement tracking
    
    Event types:
    - PARRY_ATTEMPT: User activates parry
    - PARRY_SUCCESS: Enemy attack parried (standard timing)
    - PARRY_PERFECT: Perfect timing parry (<300ms)
    - PARRY_FAILED: Window expired without enemy attack
    - COUNTERATTACK: User counterattacks after parry
    - COUNTERATTACK_BONUS: Counterattack within 3s window
    - COUNTERATTACK_LATE: Counterattack after 3s window
    - COOLDOWN_RESET: Cooldown reset triggered
    - FLAWLESS_COMBAT: Victory with 0 damage taken
    - SPEED_VICTORY: Victory under time threshold
    """
    __tablename__ = 'combat_telemetry'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(BigInteger, nullable=False, index=True)
    event_type = Column(String(50), nullable=False, index=True)
    combat_id = Column(String(100), index=True)  # Unique combat session ID
    mob_id = Column(Integer)
    mob_level = Column(Integer)
    mob_is_boss = Column(Boolean, default=False)
    
    # Timing data
    reaction_time_ms = Column(Integer)  # Parry timing
    window_duration_ms = Column(Integer, default=3000)
    counterattack_time_ms = Column(Integer)  # Time from parry to counter
    
    # Combat data
    damage_dealt = Column(Integer, default=0)
    damage_avoided = Column(Integer, default=0)
    cooldown_saved_ms = Column(Integer, default=0)
    
    # Contextual data
    user_level = Column(Integer)
    user_hp_percent = Column(Float)
    user_mana_used = Column(Integer, default=0)
    
    # Flexible metadata
    extra_metadata = Column("metadata", JSON)  # MAP TO 'metadata' IN DB to avoid immediate migration if possible, OR rename in DB too.
    timestamp = Column(TIMESTAMP, server_default=func.now(), index=True)


class ParryStats(Base):
    """
    Aggregated statistics per user for performance tracking and achievements
    
    Updated on every parry event. Used for:
    - Achievement condition checking
    - Leaderboards
    - Performance analytics
    """
    __tablename__ = 'parry_stats'
    
    user_id = Column(BigInteger, primary_key=True)
    
    # Lifetime counters
    total_parry_attempts = Column(Integer, default=0)
    total_parry_success = Column(Integer, default=0)
    total_parry_perfect = Column(Integer, default=0)
    total_parry_failed = Column(Integer, default=0)
    
    # Consecutive tracking
    max_parry_streak = Column(Integer, default=0)
    current_parry_streak = Column(Integer, default=0)
    max_perfect_streak = Column(Integer, default=0)
    current_perfect_streak = Column(Integer, default=0)
    
    # Boss achievements
    boss_parries = Column(Integer, default=0)
    perfect_boss_parries = Column(Integer, default=0)
    
    # Damage statistics
    total_damage_avoided = Column(BigInteger, default=0)
    total_counterattack_damage = Column(BigInteger, default=0)
    
    # Counterattack timing stats
    total_counters_in_window = Column(Integer, default=0)  # Within 3s
    total_counters_late = Column(Integer, default=0)  # After 3s
    
    # Performance metrics
    average_reaction_time_ms = Column(Integer)
    best_reaction_time_ms = Column(Integer)
    average_counter_time_ms = Column(Integer)
    
    # Combat perfection
    flawless_victories = Column(Integer, default=0)  # 0 damage taken
    speed_victories = Column(Integer, default=0)  # Under time threshold
    
    # Timestamps
    last_parry_at = Column(TIMESTAMP)
    updated_at = Column(TIMESTAMP, server_default=func.now(), onupdate=func.now())
