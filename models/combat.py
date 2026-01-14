from sqlalchemy import Column, Integer, String, DateTime, Boolean, ForeignKey, Float, UniqueConstraint
from database import Base
import datetime

class MobAbility(Base):
    """Defines abilities that mobs can use"""
    __tablename__ = "mob_ability"
    
    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    ability_type = Column(String, nullable=False)  # passive, active, trigger
    
    # Damage/Effect
    damage = Column(Integer, default=0)
    damage_type = Column(String, default="physical")
    
    # Targeting
    target_type = Column(String, default="single")  # single, aoe, random, lowest_hp
    max_targets = Column(Integer, default=1)
    
    # Trigger Conditions (for trigger-type abilities)
    trigger_condition = Column(String, nullable=True)  # hp_below_50, on_hit, every_3_turns
    trigger_chance = Column(Integer, default=100)  # Percentage
    
    # Effects
    status_effect = Column(String, nullable=True)  # stun, burn, confusion, mind_control
    status_duration = Column(Integer, default=0)  # turns
    status_chance = Column(Integer, default=0)
    
    # Buffs (self-buff for passive abilities)
    buff_type = Column(String, nullable=True)  # defense, evasion, damage_reflect
    buff_value = Column(Integer, default=0)
    buff_duration = Column(Integer, default=0)  # 0 = permanent while alive
    
    # Cooldown
    cooldown_turns = Column(Integer, default=0)
    
    # Description
    description = Column(String, nullable=True)
    flavor_text = Column(String, nullable=True)  # For comedic effect


class CombatParticipation(Base):
    """Tracks player contribution to mob/boss fights"""
    __tablename__ = "combat_participation"
    
    id = Column(Integer, primary_key=True)
    mob_id = Column(Integer, ForeignKey('mob.id'))
    user_id = Column(Integer, nullable=False)  # id_telegram
    
    # Damage Tracking
    damage_dealt = Column(Integer, default=0)
    hits_landed = Column(Integer, default=0)
    critical_hits = Column(Integer, default=0)
    
    # Support Tracking
    healing_done = Column(Integer, default=0)
    buffs_applied = Column(Integer, default=0)
    
    # Rewards
    exp_earned = Column(Integer, default=0)
    loot_received = Column(String, nullable=True)  # JSON array of items
    reward_claimed = Column(Boolean, default=False)
    
    # Timestamps
    first_hit_time = Column(DateTime, nullable=True)
    last_hit_time = Column(DateTime, nullable=True)
    
    # Unique constraint: one record per user per mob
    __table_args__ = (UniqueConstraint('mob_id', 'user_id', name='_mob_user_uc'),)
