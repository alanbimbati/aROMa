from sqlalchemy import Column, Integer, String, BigInteger, ForeignKey, Float, DateTime
from sqlalchemy.orm import relationship
from database import Base
import datetime

class Mount(Base):
    __tablename__ = "mounts"
    id = Column(Integer, primary_key=True)
    name = Column(String(100), unique=True, nullable=False)
    speed_bonus = Column(Integer, default=10) # Percentage or flat bonus? User said "aumentano la velocità"
    min_level = Column(Integer, default=1)
    price = Column(Integer, default=1000)
    image = Column(String(255), nullable=True)
    description = Column(String(255), nullable=True)
    rarity = Column(Integer, default=1) # 1: Common, 2: Rare, 3: Epic, 4: Legendary

class UserMount(Base):
    __tablename__ = "user_mounts"
    id = Column(Integer, primary_key=True)
    user_id = Column(BigInteger, ForeignKey('utente.id_Telegram'), nullable=False)
    mount_id = Column(Integer, ForeignKey('mounts.id'), nullable=False)
    obtained_at = Column(DateTime, default=datetime.datetime.now)
    
    # Relationship to get mount details easily
    mount = relationship("Mount")
