from sqlalchemy import Column, Integer, BigInteger, String, DateTime, ForeignKey, Float
from sqlalchemy.orm import relationship
from database import Base
import datetime

class Guild(Base):
    __tablename__ = "guilds"
    id = Column(Integer, primary_key=True)
    name = Column(String(64), unique=True, nullable=False)
    leader_id = Column(BigInteger, ForeignKey('utente.id_Telegram'), nullable=False)
    wumpa_bank = Column(Integer, default=0)
    member_limit = Column(Integer, default=5)
    
    # Upgrades
    inn_level = Column(Integer, default=1)
    armory_level = Column(Integer, default=0)
    village_level = Column(Integer, default=1)
    bordello_level = Column(Integer, default=0)
    
    # Location on pixelated map
    map_x = Column(Integer, nullable=True)
    map_y = Column(Integer, nullable=True)
    
    created_at = Column(DateTime, default=datetime.datetime.now)
    
    # Relationships
    members = relationship("GuildMember", back_populates="guild", cascade="all, delete-orphan")
    upgrades = relationship("GuildUpgrade", back_populates="guild", cascade="all, delete-orphan")

class GuildMember(Base):
    __tablename__ = "guild_members"
    id = Column(Integer, primary_key=True)
    guild_id = Column(Integer, ForeignKey('guilds.id'), nullable=False)
    user_id = Column(BigInteger, ForeignKey('utente.id_Telegram'), unique=True, nullable=False)
    role = Column(String(20), default="Member") # Leader, Officer, Member
    joined_at = Column(DateTime, default=datetime.datetime.now)
    
    guild = relationship("Guild", back_populates="members")

class GuildUpgrade(Base):
    __tablename__ = "guild_upgrades"
    id = Column(Integer, primary_key=True)
    guild_id = Column(Integer, ForeignKey('guilds.id'), nullable=False)
    upgrade_type = Column(String(32), nullable=False) # Inn, Armory, Village
    level = Column(Integer, default=1)
    cost = Column(Integer, nullable=False)
    completion_time = Column(DateTime, nullable=True) # If None, it's completed
    
    guild = relationship("Guild", back_populates="upgrades")

class GuildItem(Base):
    __tablename__ = "guild_items"
    id = Column(Integer, primary_key=True)
    guild_id = Column(Integer, ForeignKey('guilds.id'), nullable=False)
    item_name = Column(String(128), nullable=False)
    quantity = Column(Integer, default=1)
    
    guild = relationship("Guild", back_populates="items")

# Add relationship to Guild class
Guild.items = relationship("GuildItem", back_populates="guild", cascade="all, delete-orphan")
