from sqlalchemy import Column, Integer, String, DateTime
from database import Base

class Collezionabili(Base):
    __tablename__ = "collezionabili"

    id = Column(Integer, primary_key=True, autoincrement=True)
    id_telegram = Column(String, nullable=False)
    oggetto = Column(String, nullable=False)
    data_acquisizione = Column(DateTime, nullable=False)
    quantita = Column(Integer, nullable=False)
    data_utilizzo = Column(DateTime, nullable=True)
