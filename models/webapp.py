from sqlalchemy import Column, Integer, BigInteger, String, DateTime
from database import Base
import datetime


class WebLoginToken(Base):
    """One-time login link handed out by the bot. Only the hash of the token is stored."""
    __tablename__ = "web_login_token"

    id = Column(Integer, primary_key=True)
    token_hash = Column(String(64), unique=True, nullable=False)
    user_id = Column(BigInteger, nullable=False, index=True)  # id_telegram
    created_at = Column(DateTime, default=datetime.datetime.now)
    expires_at = Column(DateTime, nullable=False)
    used_at = Column(DateTime, nullable=True)
