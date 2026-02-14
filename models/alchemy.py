from sqlalchemy import Column, Integer, BigInteger, String, DateTime, ForeignKey
from database import Base
import datetime

class AlchemyQueue(Base):
    """Represents potions currently being brewed by users"""
    __tablename__ = "alchemy_queue"
    
    id = Column(Integer, primary_key=True)
    user_id = Column(BigInteger, ForeignKey('utente.id_Telegram'), nullable=False)
    potion_name = Column(String(100), nullable=False)
    
    start_time = Column(DateTime, default=datetime.datetime.now)
    completion_time = Column(DateTime, nullable=False)
    status = Column(String(20), default="in_progress") # in_progress, completed, claimed
    
    xp_gain = Column(Integer, default=0)
    
    def __repr__(self):
        return f"<AlchemyQueue(user={self.user_id}, potion='{self.potion_name}', status='{self.status}')>"
