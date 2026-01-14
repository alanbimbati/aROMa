from sqlalchemy import Column, Integer, String, Date, DateTime, Boolean, Float
from database import Base
import datetime

class Livello(Base):
    """Character class - represents unlockable characters/skins"""
    __tablename__ = "livello"
    id = Column(Integer, primary_key=True)
    livello = Column(Integer, nullable=False)  # Level requirement to unlock
    nome = Column(String, nullable=False)
    lv_premium = Column(Integer, default=0) # 0=Free, 1=Premium Only, 2=Purchasable
    exp_required = Column(Integer, nullable=True)  # Temporaneamente nullable per compatibilità
    price = Column(Integer, default=0)
    
    # Combat Stats
    elemental_type = Column(String, default="Normal") # Fire, Water, Grass, etc.
    crit_chance = Column(Integer, default=5) # Percentage (5%)
    crit_multiplier = Column(Float, default=1.5) # 1.5x damage
    
    # Evolution / Prerequisite
    required_character_id = Column(Integer, nullable=True) # ID of previous form
    
    # Character abilities (Primary is still here for backward compat, but we'll use CharacterAbility table)
    special_attack_name = Column(String, nullable=True)
    special_attack_damage = Column(Integer, default=0)
    special_attack_mana_cost = Column(Integer, default=0)
    
    image_path = Column(String, nullable=True)
    telegram_file_id = Column(String, nullable=True)  # Telegram file_id for cached images
    description = Column(String, nullable=True)
    
    # Character group (e.g., "Dragon Ball", "Crash Bandicoot")
    character_group = Column(String, nullable=True, default="General")

class CharacterAbility(Base):
    """Multiple abilities per character"""
    __tablename__ = "character_ability"
    id = Column(Integer, primary_key=True)
    character_id = Column(Integer, nullable=False) # Livello.id
    name = Column(String, nullable=False)
    damage = Column(Integer, default=0)
    mana_cost = Column(Integer, default=0)
    elemental_type = Column(String, default="Normal")
    
    # Critical Hit Stats
    crit_chance = Column(Integer, default=5) # Percentage (5%)
    crit_multiplier = Column(Float, default=1.5) # 1.5x damage
    
    # Status Effects
    status_effect = Column(String, nullable=True) # burn, poison, stun, freeze
    status_chance = Column(Integer, default=0) # % chance
    status_duration = Column(Integer, default=0) # turns
    
    description = Column(String, nullable=True)

class CharacterTransformation(Base):
    """Defines available transformations for characters"""
    __tablename__ = "character_transformation"
    id = Column(Integer, primary_key=True)
    base_character_id = Column(Integer, nullable=False)  # Livello.id of base character
    transformed_character_id = Column(Integer, nullable=False)  # Livello.id of transformed state
    transformation_name = Column(String, nullable=False)  # e.g., "Super Saiyan"
    wumpa_cost = Column(Integer, nullable=False)  # Cost to activate
    duration_days = Column(Float, nullable=False, default=2.0)  # Duration in days
    
    # Stat bonuses when transformed
    health_bonus = Column(Integer, default=0)
    mana_bonus = Column(Integer, default=0)
    damage_bonus = Column(Integer, default=0)
    
    # Progressive transformation (requires previous transformation)
    is_progressive = Column(Boolean, default=False)
    previous_transformation_id = Column(Integer, nullable=True)  # Required transformation if progressive
    
    # Level requirement for this transformation
    required_level = Column(Integer, nullable=True)  # Minimum user level required

class UserTransformation(Base):
    """Tracks active transformations for users"""
    __tablename__ = "user_transformation"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, nullable=False)  # id_telegram
    transformation_id = Column(Integer, nullable=False)  # CharacterTransformation.id
    activated_at = Column(DateTime, default=datetime.datetime.now)
    expires_at = Column(DateTime, nullable=False)
    is_active = Column(Boolean, default=True)

class Domenica(Base):
    __tablename__ = "domenica"
    id = Column(Integer, primary_key=True)
    last_day = Column('last_day', Date)
    utente = Column('utente', Integer, unique=True)

class UserCharacter(Base):
    __tablename__ = "user_character"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, nullable=False)  # id_telegram
    character_id = Column(Integer, nullable=False)  # Livello.id
    obtained_at = Column(Date, nullable=True)

