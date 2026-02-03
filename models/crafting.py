from sqlalchemy import Column, Integer, BigInteger, String, DateTime, ForeignKey, Float
from database import Base
import datetime

class CraftingQueue(Base):
    """Represents items currently being crafted in the guild armory"""
    __tablename__ = "crafting_queue"
    
    id = Column(Integer, primary_key=True)
    guild_id = Column(Integer, ForeignKey('guilds.id'), nullable=False)
    user_id = Column(BigInteger, ForeignKey('utente.id_Telegram'), nullable=False)
    equipment_id = Column(Integer, ForeignKey('equipment.id'), nullable=False)
    
    start_time = Column(DateTime, default=datetime.datetime.now)
    completion_time = Column(DateTime, nullable=False)
    status = Column(String(20), default="in_progress") # in_progress, completed, cancelled
    
    actual_rarity = Column(Integer, nullable=True) # Final rarity result after crafting
    
    # We could add relationships if needed, but for now we just need the table
