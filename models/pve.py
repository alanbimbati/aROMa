from sqlalchemy import Column, Integer, String, DateTime, Boolean, ForeignKey
from database import Base
import datetime

class Mob(Base):
    __tablename__ = "mob"
    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    health = Column(Integer, nullable=False)
    max_health = Column(Integer, nullable=False)
    spawn_time = Column(DateTime, default=datetime.datetime.now)
    is_dead = Column(Boolean, default=False)
    killer_id = Column(Integer, nullable=True) # Telegram ID of killer
    reward_claimed = Column(Boolean, default=False)
    
    # Boss flag - if True, this is a boss (previously Raid)
    is_boss = Column(Boolean, default=False)
    
    # Combat attributes
    image_path = Column(String, nullable=True)
    attack_type = Column(String, default="physical")  # physical, magic, ranged, explosive
    attack_damage = Column(Integer, default=10)
    difficulty_tier = Column(Integer, default=1)  # 1-5
    speed = Column(Integer, default=30)
    mob_level = Column(Integer, default=1)
    last_attack_time = Column(DateTime, nullable=True)
    description = Column(String, nullable=True)  # For boss descriptions
    resistance = Column(Integer, default=0) # Percentage damage reduction

class Raid(Base):
    __tablename__ = "raid"
    id = Column(Integer, primary_key=True)
    boss_name = Column(String, nullable=False)
    health = Column(Integer, nullable=False)
    max_health = Column(Integer, nullable=False)
    start_time = Column(DateTime, default=datetime.datetime.now)
    end_time = Column(DateTime, nullable=True)
    is_active = Column(Boolean, default=True)
    
    # Combat attributes
    image_path = Column(String, nullable=True)
    attack_type = Column(String, default="special")
    attack_damage = Column(Integer, default=50)
    description = Column(String, nullable=True)
    speed = Column(Integer, default=70)

class RaidParticipation(Base):
    __tablename__ = "raid_participation"
    id = Column(Integer, primary_key=True)
    raid_id = Column(Integer, ForeignKey('raid.id'))
    user_id = Column(Integer, nullable=False) # Telegram ID
    damage_dealt = Column(Integer, default=0)
