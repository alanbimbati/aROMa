from sqlalchemy import Column, Integer, String, DateTime, Boolean, ForeignKey
from database import Base
import datetime

class Dungeon(Base):
    __tablename__ = "dungeon"
    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    chat_id = Column(Integer, nullable=False)
    current_stage = Column(Integer, default=0)
    total_stages = Column(Integer, default=5)
    status = Column(String, default="registration") # registration, active, completed, failed
    created_at = Column(DateTime, default=datetime.datetime.now)
    completed_at = Column(DateTime, nullable=True)
    
    # New fields for Dragon Ball Saga Dungeons
    dungeon_def_id = Column(Integer, nullable=True) # ID from dungeons.csv
    stats = Column(String, default="{}") # JSON: {damage_taken, deaths, items_used}
    start_time = Column(DateTime, nullable=True)
    score = Column(String, nullable=True) # F, E, D, C, B, A, S, Z

class DungeonParticipant(Base):
    __tablename__ = "dungeon_participant"
    id = Column(Integer, primary_key=True)
    dungeon_id = Column(Integer, ForeignKey('dungeon.id'))
    user_id = Column(Integer, nullable=False) # Telegram ID
