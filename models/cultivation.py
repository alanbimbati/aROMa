from sqlalchemy import Column, Integer, BigInteger, String, DateTime, ForeignKey, Boolean
from database import Base
import datetime

class GardenSlot(Base):
    __tablename__ = "garden_slots"
    id = Column(Integer, primary_key=True)
    user_id = Column(BigInteger, ForeignKey('utente.id_Telegram'), nullable=False)
    slot_id = Column(Integer, nullable=False) # 1, 2, 3... based on Guild Level
    
    seed_type = Column(String(50), nullable=True) # "Semi di Wumpa", "Semi di Bacca Blu", etc.
    planted_at = Column(DateTime, nullable=True)
    completion_time = Column(DateTime, nullable=True)
    
    status = Column(String(20), default="empty") # empty, growing, ready, rotting, rotten
    
    moisture = Column(Integer, default=100) # 0-100%
    last_watered_at = Column(DateTime, nullable=True)
    rot_time = Column(DateTime, nullable=True) # When the ready plant will start rotting
