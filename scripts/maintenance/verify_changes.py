import unittest
from services.user_service import UserService
from services.item_service import ItemService
from services.pve_service import PvEService
from models.user import Utente
from models.pve import Mob
import datetime

class TestAromaFeatures(unittest.TestCase):
    def setUp(self):
        self.user_service = UserService()
        self.item_service = ItemService()
        self.pve_service = PvEService()
        self.test_id = 999999999
        self.test_target_id = 888888888
        
        # Create test users
        self.user_service.create_user(self.test_id, "test_user", "Test", "User")
        self.user_service.create_user(self.test_target_id, "test_target", "Target", "User")
        
        # Give some points
        user = self.user_service.get_user(self.test_id)
        target = self.user_service.get_user(self.test_target_id)
        self.user_service.update_user(self.test_id, {'points': 1000, 'health': 100})
        self.user_service.update_user(self.test_target_id, {'points': 1000, 'health': 100})

    def tearDown(self):
        # Cleanup is hard with this DB setup, but we can reset values
        pass

    def test_aku_aku_duration(self):
        print("\nTesting Aku Aku...")
        self.item_service.add_item(self.test_id, "Aku Aku")
        if self.item_service.use_item(self.test_id, "Aku Aku"):
            user = self.user_service.get_user(self.test_id)
            self.item_service.apply_effect(user, "Aku Aku")
        
        user = self.user_service.get_user(self.test_id) # Reload
        self.assertIsNotNone(user.invincible_until)
        # Check if duration is roughly 60 mins
        diff = user.invincible_until - datetime.datetime.now()
        minutes = diff.total_seconds() / 60
        print(f"Aku Aku duration remaining: {minutes:.2f} minutes")
        self.assertTrue(55 < minutes < 65)

    def test_turbo_luck(self):
        print("\nTesting Turbo...")
        self.item_service.add_item(self.test_id, "Turbo")
        if self.item_service.use_item(self.test_id, "Turbo"):
            user = self.user_service.get_user(self.test_id)
            self.item_service.apply_effect(user, "Turbo")
        
        user = self.user_service.get_user(self.test_id) # Reload
        self.assertEqual(user.luck_boost, 1)
        print("Turbo luck boost active.")

    def test_damage_item(self):
        print("\nTesting Damage Item...")
        self.item_service.add_item(self.test_id, "Colpisci un giocatore")
        
        user = self.user_service.get_user(self.test_id)
        target = self.user_service.get_user(self.test_target_id)
        initial_points = target.points
        
        msg = self.item_service.apply_effect(user, "Colpisci un giocatore", target_user=target)
        print(f"Item msg: {msg}")
        
        target = self.user_service.get_user(self.test_target_id) # Reload
        self.assertTrue(target.points < initial_points)
        print(f"Target points dropped from {initial_points} to {target.points}")

    def test_game_info(self):
        print("\nTesting Game Info...")
        self.user_service.update_user(self.test_id, {'platform': 'Steam', 'game_name': 'TestPlayer'})
        user = self.user_service.get_user(self.test_id)
        self.assertEqual(user.platform, 'Steam')
        self.assertEqual(user.game_name, 'TestPlayer')
        print(f"Game Info saved: {user.platform} - {user.game_name}")

    def test_pve_spawn_and_attack(self):
        print("\nTesting PvE Spawn and Attack...")
        # Force spawn
        mob_id = self.pve_service.spawn_daily_mob()
        if not mob_id:
            # Maybe already active, get it
            status = self.pve_service.get_current_mob_status()
            print(f"Mob already active: {status['name']}")
        else:
            print(f"Spawned mob id: {mob_id}")
            
        user = self.user_service.get_user(self.test_id)
        success, msg = self.pve_service.attack_mob(user, 10)
        print(f"Attack result: {msg}")
        self.assertTrue(success)
        self.assertIn("Hai inflitto 10 danni", msg)

    def test_mob_random_attack(self):
        print("\nTesting Mob Random Attack...")
        msg = self.pve_service.mob_random_attack()
        print(f"Random attack msg: {msg}")
        self.assertIsNotNone(msg)
        self.assertIn("ha attaccato", msg)

if __name__ == '__main__':
    unittest.main()
