from sqlalchemy import Column, Integer, BigInteger, String, DateTime, ForeignKey, Text
from database import Base
import datetime

class Resource(Base):
    """Represents a crafting resource"""
    __tablename__ = "resources"
    
    id = Column(Integer, primary_key=True)
    name = Column(String(100), unique=True, nullable=False)
    rarity = Column(Integer, nullable=False)
    description = Column(Text, nullable=True)
    drop_source = Column(String(20), default='mob') # mob, both
    image = Column(String(255), nullable=True) # Path to image file

class UserResource(Base):
    """Represents resources owned by a user"""
    __tablename__ = "user_resources"
    
    id = Column(Integer, primary_key=True)
    user_id = Column(BigInteger, ForeignKey('utente.id_Telegram'), nullable=False)
    resource_id = Column(Integer, ForeignKey('resources.id'), nullable=False)
    quantity = Column(Integer, default=0)
    source = Column(String(20), default='drop')
    created_at = Column(DateTime, default=datetime.datetime.now)

class RefinedMaterial(Base):
    """Represents a refined crafting material (Rottami, Materiale Pregiato, Diamante)"""
    __tablename__ = "refined_materials"
    
    id = Column(Integer, primary_key=True)
    name = Column(String(100), unique=True, nullable=False)
    rarity = Column(Integer, nullable=False) # 1: Rottami, 2: Pregiato, 3: Diamante

class UserRefinedMaterial(Base):
    """Represents refined materials owned by a user"""
    __tablename__ = "user_refined_materials"
    
    id = Column(Integer, primary_key=True)
    user_id = Column(BigInteger, ForeignKey('utente.id_Telegram'), nullable=False)
    material_id = Column(Integer, ForeignKey('refined_materials.id'), nullable=False)
    quantity = Column(Integer, default=0)

class RefineryDaily(Base):
    """Tracks the allowed resource for refinement today"""
    __tablename__ = "refinery_daily"
    
    id = Column(Integer, primary_key=True)
    date = Column(DateTime, default=datetime.datetime.now, unique=True)
    resource_id = Column(Integer, ForeignKey('resources.id'), nullable=False)

class RefineryQueue(Base):
    """Represents items currently being refined in the guild armory"""
    __tablename__ = "refinery_queue"
    
    id = Column(Integer, primary_key=True)
    user_id = Column(BigInteger, ForeignKey('utente.id_Telegram'), nullable=False)
    guild_id = Column(Integer, ForeignKey('guilds.id'), nullable=False)
    resource_id = Column(Integer, ForeignKey('resources.id'), nullable=False)
    quantity = Column(Integer, nullable=False)
    
    start_time = Column(DateTime, default=datetime.datetime.now)
    completion_time = Column(DateTime, nullable=False)
    status = Column(String(20), default="in_progress") # in_progress, completed, cancelled
