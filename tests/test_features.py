import unittest
from services.user_service import UserService
from services.item_service import ItemService
from services.shop_service import ShopService
from services.wish_service import WishService
from models.user import Utente
from database import Database

class TestFeatures(unittest.TestCase):
    def setUp(self):
        self.db = Database()
        self.user_service = UserService()
        self.item_service = ItemService()
        self.shop_service = ShopService()
        self.wish_service = WishService()
        
        # Create test user
        self.test_id = 123456789
        self.user_service.create_user(self.test_id, "testuser", "Test", "User")
        self.user = self.user_service.get_user(self.test_id)
        # Reset points
        self.user_service.update_user(self.test_id, {'points': 1000, 'premium': 1})
        self.user = self.user_service.get_user(self.test_id) # Refresh

    def tearDown(self):
        # Clean up test user
        session = self.db.get_session()
        session.query(Utente).filter_by(id_telegram=self.test_id).delete()
        session.commit()
        session.close()

    def test_buy_box_wumpa(self):
        initial_points = self.user.points
        success, msg, item = self.item_service.buy_box_wumpa(self.user) # Updated signature
        self.assertTrue(success, f"Buy box failed: {msg}")
        
        self.user = self.user_service.get_user(self.test_id) # Refresh
        self.assertEqual(self.user.points, initial_points - 25)
        print(f"Box Wumpa result: {msg}")

    def test_item_effects(self):
        # Test Turbo
        self.item_service.add_item(self.test_id, "Turbo")
        msg, _ = self.item_service.apply_effect(self.user, "Turbo") # Updated signature
        
        self.user = self.user_service.get_user(self.test_id) # Refresh
        # Check active_status_effects for turbo
        import json
        effects = json.loads(self.user.active_status_effects) if self.user.active_status_effects else []
        has_turbo = any(e.get('id') == 'turbo' for e in effects)
        self.assertTrue(has_turbo, "Turbo effect not found in active_status_effects")
        print(f"Turbo result: {msg}")
        
        # Test Aku Aku
        self.item_service.add_item(self.test_id, "Aku Aku")
        msg, _ = self.item_service.apply_effect(self.user, "Aku Aku") # Updated signature
        
        self.user = self.user_service.get_user(self.test_id) # Refresh
        self.assertIsNotNone(self.user.invincible_until)
        print(f"Aku Aku result: {msg}")

    def test_wishes(self):
        # Add spheres
        for i in range(1, 8):
            self.item_service.add_item(self.test_id, f"La Sfera del Drago Shenron {i}")
        
        has_shenron, has_porunga = self.wish_service.check_dragon_balls(self.user)
        self.assertTrue(has_shenron)
        
        initial_points = self.user.points
        msg = self.wish_service.grant_wish(self.user, "points", "Shenron")
        
        self.user = self.user_service.get_user(self.test_id) # Refresh
        self.assertEqual(self.user.points, initial_points + 1000)
        print(f"Wish result: {msg}")

if __name__ == '__main__':
    unittest.main()
