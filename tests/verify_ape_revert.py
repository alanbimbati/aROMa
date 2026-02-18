import unittest
from unittest.mock import MagicMock, patch
from datetime import datetime, timedelta
from services.transformation_service import TransformationService
from models.user import Utente
from models.system import CharacterTransformation, UserCharacter, UserTransformation

class TestApeRevert(unittest.TestCase):
    def setUp(self):
        self.trans_service = TransformationService()
        self.trans_service.db = MagicMock()
        self.session = self.trans_service.db.get_session.return_value
        self.trans_service.user_service = MagicMock()
        
        # Mock Character Data for Dynamic Check (Great Ape IDs)
        self.mock_loader = MagicMock()
        self.mock_loader.characters = {
            37: {'nome': 'Scimmione', 'id': 37, 'is_transformation': 1, 'base_character_id': 1},
            500: {'nome': 'Great Ape', 'id': 500, 'is_transformation': 1, 'base_character_id': 1},
            600: {'nome': 'Scimmione (Goku)', 'id': 600, 'is_transformation': 1, 'base_character_id': 1},
            602: {'nome': 'Scimmione (Gohan)', 'id': 602, 'is_transformation': 1, 'base_character_id': 281}
        }
        mock_char_service_init = MagicMock()
        mock_char_service_init.return_value.loader = self.mock_loader
        self.trans_service.CharacterService = mock_char_service_init
        
        # Mock User: Great Ape (500)
        self.user = MagicMock(spec=Utente)
        self.user.id_telegram = 12345
        self.user.nome = "TestUser"
        self.user.livello_selezionato = 500
        self.user.current_transformation = "Great Ape"
        self.user.transformation_expires_at = None
        self.user.resting_since = None # Not resting by default
        
        # Mock Query Results
        self.session.query.return_value.filter.return_value.all.return_value = [self.user]
        self.session.query.return_value.filter_by.return_value.first.return_value = None # Default no record found
        
    @patch('services.transformation_service.datetime')
    def test_revert_during_day(self, mock_datetime):
        # Set time to 12:00 (Day)
        mock_datetime.now.return_value = datetime(2023, 1, 1, 12, 0, 0)
        
        # Mock finding base character ownership
        mock_trans = MagicMock(spec=CharacterTransformation)
        mock_trans.base_character_id = 1 # Goku
        self.session.query.return_value.filter_by.return_value.all.return_value = [mock_trans]
        
        mock_owned = MagicMock(spec=UserCharacter)
        mock_owned.character_id = 1
        self.session.query.return_value.filter.return_value.first.return_value = mock_owned
        
        # Run Check
        reverted_count = self.trans_service.check_expired_transformations(session=self.session)
        
        # Verify
        self.assertEqual(reverted_count, 1)
        self.assertEqual(self.user.livello_selezionato, 1) # Should revert to Goku
        
    @patch('services.transformation_service.datetime')
    def test_no_revert_at_night(self, mock_datetime):
        # Set time to 22:00 (Night)
        mock_datetime.now.return_value = datetime(2023, 1, 1, 22, 0, 0)
        
        # Run Check
        reverted_count = self.trans_service.check_expired_transformations(session=self.session)
        
        # Verify
        self.assertEqual(reverted_count, 0)
        self.assertEqual(self.user.livello_selezionato, 500) # Should stay Ape

    @patch('services.transformation_service.datetime')
    def test_revert_scimmione_id_37(self, mock_datetime):
        # Set time to 10:40 (Day)
        mock_datetime.now.return_value = datetime(2023, 1, 1, 10, 40, 0)
        
        # User: Goku Great Ape (37)
        self.user.livello_selezionato = 37
        self.user.current_transformation = "Scimmione"
        
        # Mock fallback base (ID 1)
        mock_trans = MagicMock(spec=CharacterTransformation)
        mock_trans.base_character_id = 1 
        self.session.query.return_value.filter_by.return_value.first.side_effect = [None, mock_trans, None, None]
        
        # Run Check
        reverted_count = self.trans_service.check_expired_transformations(session=self.session)
        
        # Verify
        self.assertEqual(reverted_count, 1)
        self.assertEqual(self.user.livello_selezionato, 1) 

    @patch('services.transformation_service.datetime')
    def test_revert_scimmione_id_600_during_day(self, mock_datetime):
        """Test specific fix for ID 600 (Scimmione Goku) during the day"""
        # Set time to 12:00 (Day)
        mock_datetime.now.return_value = datetime(2023, 1, 1, 12, 0, 0)
        
        # User is ID 600
        self.user.livello_selezionato = 600
        self.user.current_transformation = "Scimmione (Goku)"
        
        # Setup mocks for reversion base search
        mock_trans = MagicMock(spec=CharacterTransformation)
        mock_trans.base_character_id = 1 
        self.session.query.return_value.filter_by.return_value.first.side_effect = [None, mock_trans, None, None]
        
        # Run check
        self.trans_service.check_expired_transformations(session=self.session)
        
        # Verify state change
        self.assertEqual(self.user.livello_selezionato, 1, "Should have reverted to base ID 1")

    @patch('services.transformation_service.datetime')
    def test_revert_corrupted_state_id_602(self, mock_datetime):
        """Test fix for user stuck as Ape (ID 602) but with NULL current_transformation"""
        # Set time to 12:00 (Day)
        mock_datetime.now.return_value = datetime(2023, 1, 1, 12, 0, 0)
        
        # User is ID 602 (Scimmione Gohan) but has NO transformation string
        self.user.livello_selezionato = 602
        self.user.current_transformation = None
        
        # Reversion base search mock
        mock_trans = MagicMock(spec=CharacterTransformation)
        mock_trans.base_character_id = 281 # Gohan Base
        self.session.query.return_value.filter_by.return_value.first.side_effect = [None, mock_trans, None, None]
        
        # Run check
        self.trans_service.check_expired_transformations(session=self.session)
        
        # Verify state change
        self.assertEqual(self.user.livello_selezionato, 281, "Should have reverted to Gohan Base (281)")

if __name__ == '__main__':
    unittest.main()
