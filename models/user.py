from sqlalchemy import Column, Integer, BigInteger, String, DateTime, Boolean
from database import Base
import datetime
from dateutil.relativedelta import relativedelta

class Utente(Base):
    __tablename__ = "utente"
    id = Column(Integer, primary_key=True)
    id_telegram = Column('id_Telegram', BigInteger, unique=True)
    nome  = Column('nome', String(256))  # Increased from 32 to handle long display names
    cognome = Column('cognome', String(256))  # Increased from 32
    username = Column('username', String(64), unique=True)  # Increased from 32
    exp = Column('exp', Integer)
    points = Column('money', Integer)
    cristalli_aroma = Column('cristalli_aroma', Integer, server_default="0", default=0, nullable=False)  # Premium currency for cosmetics
    livello = Column('livello', Integer)
    vita = Column('vita', Integer)
    premium = Column('premium', Integer)
    livello_selezionato = Column('livello_selezionato',Integer)
    start_tnt = Column('start_tnt',DateTime)
    end_tnt = Column('end_tnt',DateTime)
    scadenza_premium = Column(DateTime)
    abbonamento_attivo = Column(Integer, default=0)
    invincible_until = Column(DateTime, nullable=True)
    luck_boost = Column(Integer, default=0)
    
    # RPG Stats
    health = Column(Integer, default=100)
    max_health = Column(Integer, default=100)
    current_hp = Column(Integer, nullable=True)  # Current HP for combat tracking
    mana = Column(Integer, default=50)
    max_mana = Column(Integer, default=50)
    current_mana = Column(Integer, default=50)  # Current mana for combat tracking
    base_damage = Column(Integer, default=10)
    stat_points = Column(Integer, default=0)
    last_health_restore = Column(DateTime, nullable=True)
    
    # Advanced Stats
    resistance = Column(Integer, default=0)  # Damage reduction %
    crit_chance = Column(Integer, default=0)  # Critical hit chance %
    speed = Column(Integer, default=0)  # Turn order / attack frequency
    
    # Stat allocations (tracked separately for reset)
    allocated_health = Column(Integer, default=0)
    allocated_mana = Column(Integer, default=0)
    allocated_damage = Column(Integer, default=0)
    allocated_speed = Column(Integer, default=0)
    allocated_resistance = Column(Integer, default=0)
    allocated_crit = Column(Integer, default=0)
    last_stat_reset = Column(DateTime, nullable=True)  # Track last reset for cooldown
    last_attack_time = Column(DateTime, nullable=True)
    
    # Shield Mechanic
    shield_hp = Column(Integer, default=0)
    shield_max_hp = Column(Integer, default=0)
    shield_end_time = Column(DateTime, nullable=True)
    last_shield_cast = Column(DateTime, nullable=True)
    
    # Status Effects
    active_status_effects = Column(String, nullable=True)  # JSON: [{effect, duration, stacks}]
    
    # Achievement Title
    title = Column(String, nullable=True)  # Currently equipped title
    titles = Column(String, nullable=True)  # JSON: List of unlocked titles
    
    # Last character change timestamp
    last_character_change = Column(DateTime, nullable=True)
    
    # Inn / Resting
    resting_since = Column(DateTime, nullable=True)
    vigore_until = Column(DateTime, nullable=True)
    
    # Guild Inn Limits
    last_beer_usage = Column(DateTime, nullable=True)
    last_brothel_usage = Column(DateTime, nullable=True)

    # Platform (iOS, Android, Web)
    platform = Column(String, nullable=True)
    
    # Game name (custom display name)
    game_name = Column(String, nullable=True)
    
    # Chat EXP tracking (for achievements)
    chat_exp = Column(Integer, default=0)  # Total EXP gained from chatting
    
    # Economy / Anti-Inflation
    daily_wumpa_earned = Column(Integer, default=0)
    last_wumpa_reset = Column(DateTime, nullable=True)
    daily_wumpa_earned = Column(Integer, default=0)
    last_wumpa_reset = Column(DateTime, nullable=True)
    last_chat_drop_time = Column(DateTime, nullable=True)
    
    # Activity Tracking
    last_activity = Column(DateTime, nullable=True)


class Admin(Base):
    __tablename__ = "admin"
    id = Column(Integer, primary_key=True)
    id_telegram = Column('id_telegram', BigInteger)
