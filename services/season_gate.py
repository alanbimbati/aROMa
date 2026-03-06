"""
Season gate helpers for theme-based content availability.
"""

from database import Database
from models.seasons import Season
from datetime import datetime


def get_active_season_theme(session=None):
    """Return active season theme (string) or None."""
    local_session = False
    if session is None:
        session = Database().get_session()
        local_session = True

    try:
        now = datetime.now()
        season = session.query(Season).filter(
            Season.is_active == True,
            Season.start_date <= now,
            Season.end_date >= now
        ).first()
        if not season or not season.theme:
            return None
        return season.theme.strip()
    except Exception:
        return None
    finally:
        if local_session:
            session.close()


def is_theme_active(theme_name, session=None):
    """Case-insensitive check against active season theme."""
    active_theme = get_active_season_theme(session=session)
    if not active_theme or not theme_name:
        return False
    return active_theme.lower() == theme_name.strip().lower()


def is_marvel_season_active(session=None):
    """True when the currently active season theme is Marvel."""
    return is_theme_active("Marvel", session=session)
