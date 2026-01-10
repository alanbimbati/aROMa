from sqlalchemy import Column, Integer, String, DateTime, Boolean, ForeignKey, Float
from database import Base
import datetime

class Season(Base):
    """Defines a game season"""
    __tablename__ = "season"
    
    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)  # e.g., "Stagione 1: Le Origini"
    start_date = Column(DateTime, nullable=False)
    end_date = Column(DateTime, nullable=False)
    is_active = Column(Boolean, default=True)
    
    # Season-specific multipliers
    exp_multiplier = Column(Float, default=1.0)
    
    # Metadata
    description = Column(String, nullable=True)
    final_reward_name = Column(String, nullable=True)  # Name of the ultimate skin/character

class SeasonProgress(Base):
    """Tracks user progress in a specific season"""
    __tablename__ = "season_progress"
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, nullable=False)  # id_telegram
    season_id = Column(Integer, ForeignKey('season.id'))
    
    current_exp = Column(Integer, default=0)
    current_level = Column(Integer, default=1)
    
    # Track if user has purchased the premium pass for this season
    has_premium_pass = Column(Boolean, default=False)
    
    last_update = Column(DateTime, default=datetime.datetime.now)

class SeasonReward(Base):
    """Defines rewards for seasonal levels"""
    __tablename__ = "season_reward"
    
    id = Column(Integer, primary_key=True)
    season_id = Column(Integer, ForeignKey('season.id'))
    
    level_required = Column(Integer, nullable=False)
    reward_type = Column(String, nullable=False)  # skin, character, points, item
    reward_value = Column(String, nullable=False)  # ID or amount
    reward_name = Column(String, nullable=False)  # Display name
    
    is_premium = Column(Boolean, default=False)  # Free vs Premium track
    
    icon = Column(String, nullable=True)  # Emoji or icon path
