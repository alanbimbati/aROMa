from sqlalchemy import Column, Integer, BigInteger, String, DateTime, UniqueConstraint
from database import Base
import datetime


class NostrLinkChallenge(Base):
    """One-time code DM'd to an npub, to prove its owner is the Telegram user asking."""
    __tablename__ = "nostr_link_challenge"

    user_id = Column(BigInteger, primary_key=True)  # id_telegram
    npub = Column(String(70), nullable=False)
    code = Column(String(16), nullable=False)
    attempts = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.datetime.now)


class NostrBadgeOutbox(Base):
    """Badge awards waiting to reach the relays; one row per user, achievement, tier and npub."""
    __tablename__ = "nostr_badge_outbox"
    __table_args__ = (UniqueConstraint('user_id', 'achievement_key', 'tier', 'npub', name='uq_nostr_badge'),)

    id = Column(Integer, primary_key=True)
    user_id = Column(BigInteger, nullable=False)
    achievement_key = Column(String(50), nullable=False)
    tier = Column(String(20), nullable=False)
    # The npub the badge was meant for: after a change of account the same badges go out again
    npub = Column(String(70), nullable=False)
    status = Column(String(10), default='pending', index=True)  # pending | sent | failed
    attempts = Column(Integer, default=0)
    event_id = Column(String(64), nullable=True)
    error = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.now)
    sent_at = Column(DateTime, nullable=True)
