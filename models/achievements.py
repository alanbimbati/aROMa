from sqlalchemy import Column, Integer, String, DateTime, Boolean, ForeignKey, Float
from database import Base
import datetime

class Achievement(Base):
    """Defines available achievements (Declarative Rules)"""
    __tablename__ = "achievement"
    
    id = Column(Integer, primary_key=True)
    achievement_key = Column(String, unique=True, nullable=False)  # e.g., "butcher"
    name = Column(String, nullable=False)
    description = Column(String, nullable=False)
    
    # Logic
    stat_key = Column(String(50), nullable=False)   # The stat from UserStat to observe
    condition_type = Column(String(20), default='>=') # '>=', '==', '<='
    
    # Progression (JSON)
    # Structure: {
    #   "bronze": {"threshold": 100, "rewards": {"exp": 100, "title": "Novice"}},
    #   "silver": {"threshold": 500, "rewards": {"exp": 500, "title": "Apprentice"}},
    #   "gold":   {"threshold": 1000, "rewards": {"exp": 1000, "title": "Master"}}
    # }
    tiers = Column(String, nullable=False) # JSON string
    
    category = Column(String(20)) # 'combat', 'social', 'dungeon', 'collection'
    
    # Legacy / Optional fields (kept for compatibility or display)
    icon = Column(String, nullable=True)
    hidden = Column(Boolean, default=False)
    flavor_text = Column(String, nullable=True)


class UserAchievement(Base):
    """Tracks user achievement progress"""
    __tablename__ = "user_achievement"
    
    user_id = Column(Integer, primary_key=True)  # id_telegram
    achievement_key = Column(String(50), primary_key=True) # Changed to use key as PK part
    
    current_tier = Column(String(20), nullable=True) # NULL, 'bronze', 'silver', 'gold', 'platinum'
    progress_value = Column(Float, default=0.0) # Snapshot of the stat value at last check
    unlocked_at = Column(DateTime, nullable=True)
    
    # Metadata
    last_progress_update = Column(DateTime, default=datetime.datetime.now)


class GameEvent(Base):
    """Logs all significant game events for achievement tracking (Fact Table)"""
    __tablename__ = "game_event"
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, nullable=False)
    event_type = Column(String(50), nullable=False)  # mob_kill, damage_dealt, etc.
    
    value = Column(Float, default=0.0)            # The primary metric
    context = Column(String, nullable=True)       # JSON: {dungeon_id, mob_level, ...}
    
    timestamp = Column(DateTime, default=datetime.datetime.now)
    processed = Column(Boolean, default=False)  # For async stat aggregation
