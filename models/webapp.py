from sqlalchemy import Column, Integer, BigInteger, String, DateTime, Text
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


class WebCombatAction(Base):
    """A fight button pressed in the web app, waiting for the bot: only the bot plays it and writes in the chats."""
    __tablename__ = "web_combat_action"

    id = Column(Integer, primary_key=True)
    user_id = Column(BigInteger, nullable=False, index=True)  # id_telegram
    chat_id = Column(BigInteger, nullable=False)  # where the mob is: the group, or the player's private chat
    data = Column(String(64), nullable=False)  # the same callback data the chat button carries
    status = Column(String(16), nullable=False, default='pending', index=True)  # pending, running, done, expired
    ok = Column(Integer, nullable=True)
    message = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.now)
    done_at = Column(DateTime, nullable=True)
