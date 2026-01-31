from sqlalchemy import Column, Integer, String, DateTime
from database import Base
import datetime

class SystemState(Base):
    """Table for storing global system state variables"""
    __tablename__ = "system_state"
    
    key = Column(String, primary_key=True)
    value = Column(String, nullable=True)
    last_updated = Column(DateTime, default=datetime.datetime.now, onupdate=datetime.datetime.now)

    @classmethod
    def get_val(cls, session, key, default=None):
        obj = session.query(cls).filter_by(key=key).first()
        return obj.value if obj else default

    @classmethod
    def set_val(cls, session, key, value):
        obj = session.query(cls).filter_by(key=key).first()
        if not obj:
            obj = cls(key=key, value=str(value))
            session.add(obj)
        else:
            obj.value = str(value)
        session.flush()
