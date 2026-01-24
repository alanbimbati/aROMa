from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, DateTime
from database import Base
import datetime

class UserItem(Base):
    """Represents an item instance owned by a user (Inventory)"""
    __tablename__ = "user_item"
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, nullable=False) # id_telegram
    item_id = Column(Integer, ForeignKey('item.id'), nullable=False)
    
    obtained_at = Column(DateTime, default=datetime.datetime.now)
    
    # Upgrade level (e.g., +1, +2...)
    level = Column(Integer, default=0)
    
    # Whether it is currently equipped
    is_equipped = Column(Boolean, default=False)
    
    # If we want to support random stats on drop, we could add a 'random_stats' JSON column here
    # For now, we stick to base item stats + level scaling
