
import unittest
import sys
import os
from unittest.mock import MagicMock, patch

# Ensure we can import modules
sys.path.append(os.getcwd())

from services.crafting_service import CraftingService

class TestResourceSystem(unittest.TestCase):
    def setUp(self):
        self.mock_db = MagicMock()
        self.mock_session = MagicMock()
        self.mock_db.get_session.return_value = self.mock_session
        
        # Patch Database in CraftingService
        with patch('services.crafting_service.Database') as MockDB:
            MockDB.return_value = self.mock_db
            self.service = CraftingService()
            
    def test_roll_chat_drop_success(self):
        # Mock random.random, random.randint
        with patch('random.random', return_value=0.0): # 0.0 < 5.0 (chance)
            with patch('random.randint', return_value=1): # 1 item, 1 quantity
                # Mock DB result
                self.mock_session.execute.return_value.fetchone.return_value = (101, 'images/test.png')
                
                drops = self.service.roll_chat_drop(chance=5)
                
                self.assertEqual(len(drops), 1)
                self.assertEqual(drops[0][0], 101)
                self.assertEqual(drops[0][2], 'images/test.png')
                
    def test_roll_chat_drop_failure(self):
        # Mock random to fail drop
        with patch('random.random', return_value=0.9): # 90 > 5
            drops = self.service.roll_chat_drop(chance=5)
            self.assertEqual(len(drops), 0)

    def test_roll_resource_drop_mob(self):
        # Mob drop scaling
        # Level 5
        with patch('random.random', return_value=0.0): 
             with patch('random.randint', return_value=1):
                 self.mock_session.execute.return_value.fetchone.return_value = (202, 'images/res.png')
                 
                 drops = self.service.roll_resource_drop(mob_level=5, mob_is_boss=False)
                 self.assertEqual(len(drops), 1)
                 self.assertEqual(drops[0][0], 202)
                 
    def test_add_resource_drop_new(self):
        # Test adding a drop for a new resource
        # return None for existing check
        self.mock_session.execute.return_value.fetchone.return_value = None
        
        success = self.service.add_resource_drop(user_id=1, resource_id=10, quantity=1)
        
        self.assertTrue(success)
        # Verify insert called
        # We can't easily check SQL string exact match but we can check call count
        self.assertTrue(self.mock_session.execute.called)
        self.mock_session.commit.assert_called()

if __name__ == '__main__':
    unittest.main()
