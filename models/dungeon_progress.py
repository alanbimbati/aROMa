from sqlalchemy import Column, Integer, BigInteger, String, DateTime, ForeignKey
from database import Base
import datetime

class DungeonProgress(Base):
    __tablename__ = "dungeon_progress"
    id = Column(Integer, primary_key=True)
    user_id = Column(BigInteger, nullable=False) # Telegram ID
    dungeon_def_id = Column(Integer, nullable=False)
    best_rank = Column(String, nullable=True) # F-Z
    completed_at = Column(DateTime, default=datetime.datetime.now)
    times_completed = Column(Integer, default=1)
