from sqlalchemy import Column, Integer, BigInteger, String, Boolean, ForeignKey, DateTime, JSON, Text
from database import Base
import datetime

class Equipment(Base):
    """Represents an equipment blueprint/template"""
    __tablename__ = "equipment"
    
    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False)
    slot = Column(String(50), nullable=False)
    rarity = Column(Integer, default=1)
    stats_json = Column(JSON, nullable=True)
    min_level = Column(Integer, default=1)
    effect_type = Column(String(50), nullable=True)
    crafting_time = Column(Integer, default=0)
    crafting_requirements = Column(Text, nullable=True)
    description = Column(Text, nullable=True)
    set_name = Column(String(100), nullable=True)

    @property
    def special_effect_id(self):
        """Mapping for backward compatibility with pve_service"""
        return self.effect_type

class UserEquipment(Base):
    """Represents an equipment instance owned by a user"""
    __tablename__ = "user_equipment"
    
    id = Column(Integer, primary_key=True)
    user_id = Column(BigInteger, nullable=False)
    equipment_id = Column(Integer, ForeignKey('equipment.id'), nullable=False)
    equipped = Column(Boolean, default=False)
    slot_equipped = Column(String(50), nullable=True) # e.g. "ring_1", "ring_2"
    created_at = Column(DateTime, default=datetime.datetime.now)
    rarity = Column(Integer, default=1)   # Instance rarity (can differ from blueprint)
    stats_json = Column(JSON, nullable=True) # Instance stats (RNG)
