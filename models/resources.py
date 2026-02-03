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

class UserResource(Base):
    """Represents resources owned by a user"""
    __tablename__ = "user_resources"
    
    id = Column(Integer, primary_key=True)
    user_id = Column(BigInteger, ForeignKey('utente.id_Telegram'), nullable=False)
    resource_id = Column(Integer, ForeignKey('resources.id'), nullable=False)
    quantity = Column(Integer, default=0)
    source = Column(String(20), default='drop')
    created_at = Column(DateTime, default=datetime.datetime.now)
