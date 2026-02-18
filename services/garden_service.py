"""
Garden Service - Wrapper around CultivationService with level/XP tracking.
Provides get_garden_info() used in the profile display.
"""
from database import Database
from models.stats import UserStat


class GardenService:
    MAX_GARDEN_LEVEL = 50

    def __init__(self):
        self.db = Database()

    def get_garden_info(self, user_id):
        """Get user garden level and XP (used in profile)."""
        session = self.db.get_session()
        try:
            xp_stat = session.query(UserStat).filter_by(
                user_id=user_id, stat_key='garden_xp'
            ).first()
            level_stat = session.query(UserStat).filter_by(
                user_id=user_id, stat_key='garden_level'
            ).first()

            return {
                "level": int(level_stat.value) if level_stat else 1,
                "xp": int(xp_stat.value) if xp_stat else 0,
            }
        finally:
            session.close()

    def add_garden_xp(self, user_id, amount, session=None):
        """Add XP to user's garden skill and check for level up."""
        local_session = False
        if not session:
            session = self.db.get_session()
            local_session = True

        try:
            info = self.get_garden_info(user_id)
            current_xp = info['xp']
            current_level = info['level']

            if current_level >= self.MAX_GARDEN_LEVEL:
                return False

            new_xp = current_xp + amount
            new_level = current_level

            while True:
                if new_level >= self.MAX_GARDEN_LEVEL:
                    new_level = self.MAX_GARDEN_LEVEL
                    break
                xp_needed = 100 * (new_level * (new_level + 1) // 2)
                if new_xp >= xp_needed:
                    new_level += 1
                else:
                    break

            # Update XP
            xp_entry = session.query(UserStat).filter_by(
                user_id=user_id, stat_key='garden_xp'
            ).first()
            if xp_entry:
                xp_entry.value = new_xp
            else:
                xp_entry = UserStat(user_id=user_id, stat_key='garden_xp', value=new_xp)
                session.add(xp_entry)

            # Update Level
            lvl_entry = session.query(UserStat).filter_by(
                user_id=user_id, stat_key='garden_level'
            ).first()
            if lvl_entry:
                lvl_entry.value = new_level
            else:
                lvl_entry = UserStat(user_id=user_id, stat_key='garden_level', value=new_level)
                session.add(lvl_entry)

            if local_session:
                session.commit()

            return new_level > current_level
        finally:
            if local_session:
                session.close()
