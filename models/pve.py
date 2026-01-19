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
    chat_id = Column(Integer, nullable=True) # Group where mob was spawned
    
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
    
    # Advanced Mechanics
    passive_abilities = Column(String, nullable=True)  # JSON array of ability IDs
    active_abilities = Column(String, nullable=True)   # JSON array of ability IDs
    ai_behavior = Column(String, default="aggressive")  # aggressive, defensive, tactical
    phase_thresholds = Column(String, nullable=True)   # JSON: {50: "phase2", 25: "phase3"}
    current_phase = Column(Integer, default=1)
    
    # Buffs/Debuffs
    active_buffs = Column(String, nullable=True)  # JSON: [{buff_type, value, duration}]
    
    # Targeting variety
    last_target_id = Column(Integer, nullable=True)
    aggro_target_id = Column(Integer, nullable=True)
    aggro_end_time = Column(DateTime, nullable=True)
    
    # NEW: Track the spawn message ID to delete it later
    last_message_id = Column(Integer, nullable=True)
    
    # Dungeon integration
    dungeon_id = Column(Integer, ForeignKey('dungeon.id'), nullable=True)

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
