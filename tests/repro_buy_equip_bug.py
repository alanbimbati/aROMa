import sys
import os
import unittest
from unittest.mock import MagicMock, patch

# Path adjustment
sys.path.append(os.getcwd())

from services.character_service import CharacterService
from models.user import Utente
from models.system import UserCharacter

class TestCharacterShopLogic(unittest.TestCase):
    def setUp(self):
        self.cs = CharacterService()
        self.user = Utente(id_telegram=123, livello=10, points=1000) # User level 10
        
    @patch('services.character_loader.CharacterLoader.get_character_by_id')
    @patch('database.Database.get_session')
    def test_ownership_vs_level_lock(self, mock_session_factory, mock_get_char):
        # Mock Broly: Level 50, purchasable (lv_premium=2)
        broly = {
            'id': 999,
            'nome': 'Broly',
            'livello': 50,
            'lv_premium': 2,
            'price': 500
        }
        mock_get_char.return_value = broly
        
        # Mock session and DB responses
        session = MagicMock()
        mock_session_factory.return_value = session
        
        # Scenario: User OWNS Broly but is level 10
        ownership = UserCharacter(user_id=123, character_id=999)
        session.query(UserCharacter).filter_by.return_value.first.return_value = ownership
        
        # Test 1: is_character_unlocked should be FALSE because level 10 < 50
        unlocked = self.cs.is_character_unlocked(self.user, 999)
        print(f"Unlocked (Level 10, Broly 50): {unlocked}")
        self.assertFalse(unlocked, "Should be locked due to level")
        
        # Test 2: is_character_owned should be TRUE (Broly is owned)
        owned = self.cs.is_character_owned(self.user, 999)
        print(f"Owned (Broly): {owned}")
        self.assertTrue(owned, "User should own Broly regardless of level")
        
        # Test 3: equip_character should fail with level error
        # (This is expected, but the UI should show Equip button regardless)
        success, msg = self.cs.equip_character(self.user, 999)
        print(f"Equip Success: {success}, Msg: {msg}")
        self.assertFalse(success)
        self.assertIn("Livello insufficiente", msg)

if __name__ == "__main__":
    unittest.main()
