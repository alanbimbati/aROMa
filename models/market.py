from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Boolean, BigInteger
from sqlalchemy.orm import relationship
from database import Base
import datetime

class MarketListing(Base):
    __tablename__ = 'market_listings'

    id = Column(Integer, primary_key=True)
    seller_id = Column(BigInteger, ForeignKey('utente.id_Telegram'), nullable=False)
    item_name = Column(String, nullable=False)
    quantity = Column(Integer, default=1)
    price_per_unit = Column(Integer, nullable=False)
    created_at = Column(DateTime, default=datetime.datetime.now)
    expires_at = Column(DateTime)
    
    # Status: 'active', 'sold', 'cancelled', 'expired'
    status = Column(String, default='active')
    
    buyer_id = Column(BigInteger, ForeignKey('utente.id_Telegram'), nullable=True)
    sold_at = Column(DateTime, nullable=True)

    # Relationships
    seller = relationship("Utente", foreign_keys=[seller_id], backref="listings_sold")
    buyer = relationship("Utente", foreign_keys=[buyer_id], backref="listings_bought")

    def __repr__(self):
        return f"<MarketListing(id={self.id}, item={self.item_name}, seller={self.seller_id}, status={self.status})>"
