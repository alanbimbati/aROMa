from sqlalchemy import Column, Integer, BigInteger, String, Float, DateTime, ForeignKey
from database import Base
import datetime

class UserStat(Base):
    """
    Cache for derived statistics to avoid querying the huge game_event table constantly.
    Stores aggregated values like 'total_damage', 'total_kills', etc.
    """
    __tablename__ = "user_stat"
    
    user_id = Column(BigInteger, primary_key=True)  # id_telegram
    stat_key = Column(String(50), primary_key=True)   # e.g., 'total_damage', 'total_kills'
    value = Column(Float, default=0.0)
    last_updated = Column(DateTime, default=datetime.datetime.now, onupdate=datetime.datetime.now)
    
    def __repr__(self):
        return f"<UserStat(user={self.user_id}, key='{self.stat_key}', value={self.value})>"
