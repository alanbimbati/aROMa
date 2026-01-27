from sqlalchemy import Column, Integer, BigInteger, String, DateTime, Date, ForeignKey
from database import Base
import datetime

class CharacterOwnership(Base):
    """Tracks which users currently own/use each character"""
    __tablename__ = "character_ownership"
    
    id = Column(Integer, primary_key=True)
    character_id = Column(Integer, nullable=False)  # Livello.id
    user_id = Column(BigInteger, nullable=False)  # Utente.id_telegram
    equipped_at = Column(DateTime, nullable=False, default=datetime.datetime.now)
    last_change_date = Column(Date, nullable=True)  # Track for weekly restriction
