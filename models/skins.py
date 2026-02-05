from sqlalchemy import Column, Integer, BigInteger, String, Boolean
from database import Base

class UserSkin(Base):
    """Tracks character skins owned by users"""
    __tablename__ = "user_skins"
    
    id = Column(Integer, primary_key=True)
    user_id = Column(BigInteger, nullable=False, index=True)  # id_telegram
    character_id = Column(Integer, nullable=False, index=True)  # Livello.id
    skin_id = Column(Integer, nullable=False)  # ID from skins.csv
    skin_name = Column(String, nullable=False) # Name cached from skins.csv
    gif_path = Column(String, nullable=False)  # Path cached from skins.csv
    is_equipped = Column(Boolean, default=False)
