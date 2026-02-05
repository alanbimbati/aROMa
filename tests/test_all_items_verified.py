
import unittest
from unittest.mock import MagicMock, patch, ANY
import sys
import os
import json
import datetime

# Add project root to path
sys.path.append(os.getcwd())

from services.item_service import ItemService
from services.wish_service import WishService
from models.user import Utente

class TestAllItemsVerified(unittest.TestCase):
    def setUp(self):
        # Mock dependencies
        self.mock_db = MagicMock()
        self.mock_user_service = MagicMock()
        self.mock_event_dispatcher = MagicMock()
        self.mock_item_service = MagicMock()
        
        # Patch dependencies in ItemService AND WishService
        patcher_db = patch('services.item_service.Database', return_value=self.mock_db)
        patcher_us = patch('services.item_service.UserService', return_value=self.mock_user_service)
        patcher_ed = patch('services.item_service.EventDispatcher', return_value=self.mock_event_dispatcher)
        
        # We need a separate patcher set for WishService because we want to Mock ItemService there
        patcher_ws_db = patch('services.wish_service.Database', return_value=self.mock_db)
        patcher_ws_us = patch('services.wish_service.UserService', return_value=self.mock_user_service)
        patcher_ws_is = patch('services.wish_service.ItemService', return_value=self.mock_item_service) # Mock IS for WishService

        self.addCleanup(patcher_db.stop)
        self.addCleanup(patcher_us.stop)
        self.addCleanup(patcher_ed.stop)
        self.addCleanup(patcher_ws_db.stop)
        self.addCleanup(patcher_ws_us.stop)
        self.addCleanup(patcher_ws_is.stop)
        
        self.mock_db_cls = patcher_db.start()
        self.mock_us_cls = patcher_us.start()
        self.mock_ed_cls = patcher_ed.start()
        patcher_ws_db.start()
        patcher_ws_us.start()
        patcher_ws_is.start()
        
        # Item Service Setup (Real one for Item tests, but with mocked deps)
        self.item_service = ItemService()
        self.item_service.user_service = self.mock_user_service
        self.item_service.event_dispatcher = self.mock_event_dispatcher
        
        # Wish Service Setup (with mocked ItemService)
        self.wish_service = WishService()
        self.wish_service.item_service = self.mock_item_service # Explicitly set mock
        self.wish_service.user_service = self.mock_user_service
        self.wish_service.db = self.mock_db
        
        # Setup dummy user
        self.user = Utente(id_telegram=12345, username="Tester", points=100)
        self.target_user = Utente(id_telegram=67890, username="Target", points=100)

    # --- POTIONS TESTS ---
    @patch('services.potion_service.PotionService')
    def test_health_potion(self, MockPotionService):
        mock_ps = MockPotionService.return_value
        mock_ps.get_potion_by_name.return_value = {'tipo': 'health_potion'}
        mock_ps.apply_potion_effect.return_value = (True, "Healed")
        
        msg, effect = self.item_service.apply_effect(self.user, "Pozione Salute")
        
        mock_ps.apply_potion_effect.assert_called_with(self.user, "Pozione Salute", session=ANY)
        self.assertEqual(msg, "Healed")

    # --- UTILITY ITEMS TESTS ---
    def test_turbo_activation(self):
        self.user.active_status_effects = None
        
        msg, effect = self.item_service.apply_effect(self.user, "Turbo")
        
        self.assertIn("Turbo attivato", msg)
        # Verify user service update was called with correct JSON
        self.mock_user_service.update_user.assert_called_once()
        args = self.mock_user_service.update_user.call_args
        self.assertEqual(args[0][0], 12345)
        self.assertIn('"id": "turbo"', args[0][1]['active_status_effects'])

    def test_aku_aku_activation(self):
        msg, effect = self.item_service.apply_effect(self.user, "Aku Aku")
        
        self.assertIn("INVINCIBILE", msg)
        self.mock_user_service.update_user.assert_called_once()
        args = self.mock_user_service.update_user.call_args
        self.assertIn('invincible_until', args[0][1])

    def test_cassa_opening(self):
        msg, effect = self.item_service.apply_effect(self.user, "Cassa")
        
        self.assertIn("Hai aperto la Cassa", msg)
        self.mock_user_service.add_points.assert_called_once()
        # Verify points added > 0
        added_points = self.mock_user_service.add_points.call_args[0][1]
        self.assertTrue(5 <= added_points <= 15)

    # --- OFFENSIVE ITEMS (TNT/NITRO) TESTS ---
    def test_tnt_vs_mob(self):
        item_name = "TNT"
        mock_mob = MagicMock()
        mock_mob.id = 999
        mock_mob.name = "TestMob"
        mock_mob.max_health = 1000
        
        msg, effect = self.item_service.apply_effect(self.user, item_name, target_mob=mock_mob)
        
        self.assertIn("contro TestMob", msg)
        self.assertIsNotNone(effect)
        self.assertEqual(effect['type'], 'mob_drop')
        self.assertEqual(effect['percent'], 0.15)
        self.assertEqual(effect['damage'], 100) # 10% of 1000

    def test_nitro_vs_player(self):
        item_name = "Nitro"
        
        msg, effect = self.item_service.apply_effect(self.user, item_name, target_user=self.target_user)
        
        self.assertIn("contro Target", msg)
        self.assertIn("Ha perso", msg)
        self.assertIsNotNone(effect)
        self.assertEqual(effect['type'], 'wumpa_drop')
        # Check that points were removed from target
        self.mock_user_service.add_points.assert_called_once()
        self.assertEqual(self.mock_user_service.add_points.call_args[0][0], self.target_user) # Target user obj
        self.assertTrue(self.mock_user_service.add_points.call_args[0][1] < 0) # Negative points

    def test_tnt_trap_placement(self):
        # No target specified = Trap
        msg, effect = self.item_service.apply_effect(self.user, "TNT")
        
        self.assertIn("Piazzata", msg)
        self.assertIsNotNone(effect)
        self.assertEqual(effect['type'], 'tnt_trap')
        self.assertEqual(effect['type'], 'tnt_trap')

    # --- PVP ITEMS TESTS ---
    def test_steal_points(self): # Mira un giocatore
        msg, effect = self.item_service.apply_effect(self.user, "Mira un giocatore", target_user=self.target_user)
        
        self.assertIn("Hai rubato", msg)
        # Verify points removed from target AND added to user
        self.assertEqual(self.mock_user_service.add_points.call_count, 2)
        
    def test_hit_player(self): # Colpisci un giocatore
        msg, effect = self.item_service.apply_effect(self.user, "Colpisci un giocatore", target_user=self.target_user)
        
        self.assertIn("Hai colpito", msg)
        self.assertIsNotNone(effect)
        self.assertEqual(effect['type'], 'wumpa_drop')
        # Points removed from target only
        self.mock_user_service.add_points.assert_called_once()
        self.assertTrue(self.mock_user_service.add_points.call_args[0][1] < 0)

    # --- DRAGON BALLS TESTS ---
    def test_dragon_balls_collection(self):
        # Setup mock to return 1 for all spheres
        def get_item_side_effect(user_id, item_name):
            if "Sfera del Drago Shenron" in item_name:
                return 1
            return 0
            
        self.mock_item_service.get_item_by_user.side_effect = get_item_side_effect
        
        has_shenron, has_porunga = self.wish_service.check_dragon_balls(self.user)
        
        self.assertTrue(has_shenron)
        self.assertFalse(has_porunga)
        # Verify it checked all 7
        self.assertEqual(self.mock_item_service.get_item_by_user.call_count, 14) # 7 Shenron + 7 Porunga

    def test_shenron_wish_wumpa(self):
        # Grant wish
        msg = self.wish_service.grant_wish(self.user, "wumpa", dragon_type="Shenron")
        
        self.assertIn("SHENRON HA ESAUDITO", msg)
        # Verify 7 spheres were consumed
        self.assertEqual(self.mock_item_service.use_item.call_count, 7)
        # Verify points added
        self.mock_user_service.add_points_by_id.assert_called_once()

    def tearDown(self):
        # We don't strictly need this because we use addCleanup for patchers,
        # but for DB cleanup it's good practice.
        pass

if __name__ == '__main__':
    unittest.main()
