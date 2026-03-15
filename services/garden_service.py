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
        """Get user garden level and XP (using standardized CraftingService)"""
        from services.crafting_service import CraftingService
        cs = CraftingService()
        return cs.get_profession_info(user_id, profession_name='gardener')

    def add_garden_xp(self, user_id, amount, session=None):
        """Add XP (DEPRECATED: Use CraftingService.add_profession_xp directly)"""
        from services.crafting_service import CraftingService
        cs = CraftingService()
        return cs.add_profession_xp(user_id, amount, profession_name='gardener', session=session)
