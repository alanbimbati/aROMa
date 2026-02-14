import pytest
from services.equipment_service import EquipmentService
from services.user_service import UserService
from models.equipment import Equipment, UserEquipment
from models.user import Utente
from database import Database

@pytest.fixture
def equipment_service():
    return EquipmentService()

@pytest.fixture
def user_service():
    return UserService()

@pytest.fixture
def test_user_id():
    return 888888888  # Test user ID for scouter tests

@pytest.fixture
def setup_test_user_and_scouter(test_user_id):
    """Create test user and scouter equipment"""
    db = Database()
    session = db.get_session()
    
    try:
        # Clean up existing test data
        session.query(UserEquipment).filter_by(user_id=test_user_id).delete()
        session.query(Utente).filter_by(id_telegram=test_user_id).delete()
        
        # Create test user
        user = Utente()
        user.id_telegram = test_user_id
        user.username = "test_scouter_user"
        user.nome = "Scouter"
        user.cognome = "Tester"
        user.vita = 100
        user.exp = 0
        user.livello = 1
        user.points = 100
        session.add(user)
        session.commit()
        
        # Get a scouter from equipment table (should exist from fix_scouter_effect.py)
        scouter = session.query(Equipment).filter(Equipment.name.ilike('%scouter%')).first()
        
        if not scouter:
            pytest.skip("No scouter equipment found in database")
        
        yield {
            'user_id': test_user_id,
            'scouter_id': scouter.id
        }
        
        # Cleanup
        session.query(UserEquipment).filter_by(user_id=test_user_id).delete()
        session.query(Utente).filter_by(id_telegram=test_user_id).delete()
        session.commit()
    finally:
        session.close()

class TestScouterScanFunctionality:
    """Test suite for Scouter scan functionality"""
    
    def test_user_without_scouter_cannot_scan(self, setup_test_user_and_scouter):
        """User without equipped scouter should not be able to scan"""
        user_id = setup_test_user_and_scouter['user_id']
        
        # Import the function from main.py
        import sys
        sys.path.insert(0, '/home/alan/Documenti/Coding/aroma')
        from main import has_equipped_scouter
        
        # User has no equipment, should return False
        assert not has_equipped_scouter(user_id)
    
    def test_user_with_equipped_scouter_can_scan(self, equipment_service, setup_test_user_and_scouter):
        """User with equipped scouter should be able to scan"""
        user_id = setup_test_user_and_scouter['user_id']
        scouter_id = setup_test_user_and_scouter['scouter_id']
        
        # Give user a scouter
        db = Database()
        session = db.get_session()
        try:
            user_equipment = UserEquipment()
            user_equipment.user_id = user_id
            user_equipment.equipment_id = scouter_id
            user_equipment.equipped = True
            user_equipment.slot_equipped = "Accessory"
            session.add(user_equipment)
            session.commit()
        finally:
            session.close()
        
        # Import the function from main.py
        import sys
        sys.path.insert(0, '/home/alan/Documenti/Coding/aroma')
        from main import has_equipped_scouter
        
        # User has equipped scouter, should return True
        assert has_equipped_scouter(user_id)
    
    def test_scouter_has_correct_effect_type(self):
        """Verify all scouters have 'scan' effect_type"""
        db = Database()
        session = db.get_session()
        
        try:
            scouters = session.query(Equipment).filter(Equipment.name.ilike('%scouter%')).all()
            
            assert len(scouters) > 0, "No scouters found in database"
            
            for scouter in scouters:
                assert scouter.effect_type == 'scan', f"Scouter '{scouter.name}' has wrong effect_type: {scouter.effect_type}"
        finally:
            session.close()
    
    def test_unequipped_scouter_does_not_grant_scan(self, equipment_service, setup_test_user_and_scouter):
        """User with unequipped scouter in inventory cannot scan"""
        user_id = setup_test_user_and_scouter['user_id']
        scouter_id = setup_test_user_and_scouter['scouter_id']
        
        # Give user a scouter but DON'T equip it
        db = Database()
        session = db.get_session()
        try:
            user_equipment = UserEquipment()
            user_equipment.user_id = user_id
            user_equipment.equipment_id = scouter_id
            user_equipment.equipped = False  # NOT equipped
            session.add(user_equipment)
            session.commit()
        finally:
            session.close()
        
        # Import the function from main.py
        import sys
        sys.path.insert(0, '/home/alan/Documenti/Coding/aroma')
        from main import has_equipped_scouter
        
        # User has scouter but not equipped, should return False
        assert not has_equipped_scouter(user_id)

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
