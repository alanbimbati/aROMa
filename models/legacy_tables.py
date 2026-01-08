from sqlalchemy import Column, Integer, String
from database import Base

class Points(Base):
    __tablename__ = "points"
    id = Column(Integer, primary_key=True)
    numero = Column(Integer)
    gruppo = Column(Integer)
    nome = Column(String(64))

class Gruppo(Base):
    __tablename__ = "gruppo"
    id = Column(Integer, primary_key=True)
    nome = Column(String(64))
    link = Column(String(64))

class GiocoAroma(Base):
    __tablename__ = "giocoaroma"
    id = Column(Integer, primary_key=True)
    nome = Column(String)
    descrizione = Column(String)
    link = Column(String)
    from_chat = Column(String)
    messageid = Column(Integer)
