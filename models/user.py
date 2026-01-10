from sqlalchemy import Column, Integer, String, DateTime, Boolean
from database import Base
import datetime
from dateutil.relativedelta import relativedelta

class Utente(Base):
    __tablename__ = "utente"
    id = Column(Integer, primary_key=True)
    id_telegram = Column('id_Telegram', Integer, unique=True)
    nome  = Column('nome', String(32))
    cognome = Column('cognome', String(32))
    username = Column('username', String(32), unique=True)
    exp = Column('exp', Integer)
    points = Column('money', Integer)
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
    
    # Stat allocations (tracked separately for reset)
    allocated_health = Column(Integer, default=0)
    allocated_mana = Column(Integer, default=0)
    allocated_damage = Column(Integer, default=0)
    allocated_speed = Column(Integer, default=0)
    allocated_resistance = Column(Integer, default=0)
    allocated_crit_rate = Column(Integer, default=0)
    last_stat_reset = Column(DateTime, nullable=True)  # Track last reset for cooldown
    last_attack_time = Column(DateTime, nullable=True)
    
    # Status Effects
    active_status_effects = Column(String, nullable=True)  # JSON: [{effect, duration, stacks}]
    
    # Achievement Title
    title = Column(String, nullable=True)  # Current equipped title from achievements
    titles = Column(String, nullable=True)  # JSON list of all earned titles
    
    # Character ownership
    last_character_change = Column('last_character_change', DateTime, nullable=True)  # For weekly restriction

    # Game Info
    platform = Column(String(50), nullable=True)
    game_name = Column(String(100), nullable=True)

class Admin(Base):
    __tablename__ = "admin"
    id = Column(Integer, primary_key=True)
    id_telegram = Column('id_telegram',Integer)

