from sqlalchemy import Column, Integer, BigInteger, String, DateTime, ForeignKey, Float
from sqlalchemy.orm import relationship
from database import Base
import datetime

class GuildDungeonStats(Base):
    __tablename__ = "guild_dungeon_stats"
    id = Column(Integer, primary_key=True)
    guild_id = Column(Integer, ForeignKey('guilds.id'), nullable=False)
    dungeon_id = Column(Integer, nullable=False) # Maps to a specific Dungeon instance ID
    total_damage = Column(BigInteger, default=0)
    
    # Optional: Track if this record has been processed for rewards
    rewards_processed = Column(Integer, default=0) # 0=No, 1=Yes
    
    created_at = Column(DateTime, default=datetime.datetime.now)
    updated_at = Column(DateTime, default=datetime.datetime.now, onupdate=datetime.datetime.now)
    
    guild = relationship("Guild")
