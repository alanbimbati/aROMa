from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, JSON, Enum
from database import Base
import enum

class ItemRarity(enum.Enum):
    COMMON = "Common"
    UNCOMMON = "Uncommon"
    RARE = "Rare"
    EPIC = "Epic"
    LEGENDARY = "Legendary"
    MYTHIC = "Mythic"

class ItemSlot(enum.Enum):
    HELMET = "Helmet"
    SHOULDERS = "Shoulders"
    CHEST = "Chest"
    GLOVES = "Gloves"
    PANTS = "Pants"
    SHOES = "Shoes"
    RING = "Ring"
    EARRING = "Earring"

class ItemSet(Base):
    """Defines a set of items that grant bonuses when equipped together"""
    __tablename__ = "item_set"
    
    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    description = Column(String, nullable=True)
    
    # JSON structure: { "2": {"str": 10, "vit": 10}, "4": {"damage_percent": 5} }
    bonuses = Column(JSON, nullable=False, default={})

class Item(Base):
    """Defines a base item template"""
    __tablename__ = "item"
    
    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    description = Column(String, nullable=True)
    
    rarity = Column(String, nullable=False) # Store as string for simplicity or use Enum
    slot = Column(String, nullable=False)
    
    # Base stats granted by the item
    # JSON structure: { "health": 100, "strength": 5, "crit_chance": 1 }
    stats = Column(JSON, nullable=False, default={})
    
    set_id = Column(Integer, ForeignKey('item_set.id'), nullable=True)
    
    # Special effect identifier (e.g., "potara_fusion", "scouter_scan")
    special_effect_id = Column(String, nullable=True)
    
    image_path = Column(String, nullable=True)
    
    # Price in Wumpa if sold/bought
    price = Column(Integer, default=0)
    is_tradable = Column(Boolean, default=True)
