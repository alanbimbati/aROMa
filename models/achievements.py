from sqlalchemy import Column, Integer, String, DateTime, Boolean, ForeignKey, Float
from database import Base
import datetime

class Achievement(Base):
    """Defines available achievements"""
    __tablename__ = "achievement"
    
    id = Column(Integer, primary_key=True)
    achievement_key = Column(String, unique=True, nullable=False)  # e.g., "first_blood"
    name = Column(String, nullable=False)
    description = Column(String, nullable=False)
    
    # Category
    category = Column(String, nullable=False)  # combat, damage, support, meme, special
    
    # Progression
    tier = Column(String, default="bronze")  # bronze, silver, gold, platinum
    is_progressive = Column(Boolean, default=False)  # Can be earned multiple times
    max_progress = Column(Integer, default=1)  # For progressive achievements
    
    # Trigger
    trigger_event = Column(String, nullable=False)  # mob_kill, damage_dealt, crit_hit
    trigger_condition = Column(String, nullable=True)  # JSON: {min_damage: 1000}
    
    # Rewards
    reward_points = Column(Integer, default=0)
    reward_title = Column(String, nullable=True)
    cosmetic_reward = Column(String, nullable=True)  # Badge, icon, etc.
    
    # Display
    icon = Column(String, nullable=True)
    hidden = Column(Boolean, default=False)  # Hidden until unlocked
    
    # Flavor
    flavor_text = Column(String, nullable=True)


class UserAchievement(Base):
    """Tracks user achievement progress"""
    __tablename__ = "user_achievement"
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, nullable=False)  # id_telegram
    achievement_id = Column(Integer, ForeignKey('achievement.id'))
    
    # Progress
    current_progress = Column(Integer, default=0)
    is_completed = Column(Boolean, default=False)
    completion_date = Column(DateTime, nullable=True)
    
    # Metadata
    times_earned = Column(Integer, default=0)  # For repeatable achievements
    last_progress_update = Column(DateTime, default=datetime.datetime.now)


class GameEvent(Base):
    """Logs all significant game events for achievement tracking"""
    __tablename__ = "game_event"
    
    id = Column(Integer, primary_key=True)
    event_type = Column(String, nullable=False)  # mob_kill, damage_dealt, crit_hit, etc.
    user_id = Column(Integer, nullable=True)  # Can be null for system events
    
    # Event Data
    event_data = Column(String, nullable=True)  # JSON with event-specific data
    
    # Context
    mob_id = Column(Integer, nullable=True)
    combat_id = Column(Integer, nullable=True)
    
    # Timestamp
    timestamp = Column(DateTime, default=datetime.datetime.now)
    
    # Processing
    processed_for_achievements = Column(Boolean, default=False)
