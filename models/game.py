from sqlalchemy import Column, Integer, String, Boolean, Text
from database import Base

class GameInfo(Base):
    __tablename__ = 'games'

    id = Column(Integer, primary_key=True, autoincrement=True)
    title = Column(String, nullable=False)
    platform = Column(String, nullable=True)
    genre = Column(Text, nullable=True)
    description = Column(Text, nullable=True)
    language = Column(String, nullable=True)
    year = Column(Integer, nullable=True)
    region = Column(String, nullable=True)
    message_link = Column(String, nullable=False,unique=True)
    premium      = Column(Integer,nullable=True)

class Steam(Base):
    __tablename__ = "steam"
    id = Column(Integer, primary_key=True)
    titolo = Column('titolo',String(64))
    titolone = Column('titolone',Boolean)
    preso_da = Column('preso_da',String(64))
    steam_key = Column('steam_key', String(32),unique=True)

class GiocoUtente(Base):
    __tablename__ = "giocoutente"
    id = Column(Integer, primary_key=True)
    id_telegram = Column('id_Telegram', Integer)
    piattaforma = Column('piattaforma', String)
    nome        = Column('nome', String)

class NomiGiochi(Base):
    __tablename__ = "nomigiochi"
    id = Column(Integer, primary_key=True)
    id_telegram = Column('id_telegram',Integer)
    id_nintendo = Column('id_nintendo',String(256))
    id_ps = Column('id_ps',String(256))
    id_xbox = Column('id_xbox',String(256))
    id_steam = Column('id_steam',String(256))
