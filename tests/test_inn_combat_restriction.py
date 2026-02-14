import pytest
import datetime
from services.user_service import UserService
from models.user import Utente
from database import Database

@pytest.fixture
def user_service():
    return UserService()

@pytest.fixture
def test_user_id():
    return 999999999  # Test user ID

@pytest.fixture
def setup_test_user(test_user_id):
    """Create a test user for combat restriction tests"""
    db = Database()
    session = db.get_session()
    
    try:
        # Clean up existing test user
        session.query(Utente).filter_by(id_telegram=test_user_id).delete()
        
        # Create fresh test user
        user = Utente()
        user.id_telegram = test_user_id
        user.username = "test_inn_user"
        user.nome = "Test"
        user.cognome = "User"
        user.vita = 100
        user.exp = 0
        user.livello = 1
        user.points = 100
        user.last_activity = None
        
        session.add(user)
        session.commit()
        yield test_user_id
        
        # Cleanup
        session.query(Utente).filter_by(id_telegram=test_user_id).delete()
        session.commit()
    finally:
        session.close()

class TestInnCombatRestriction:
    """Test suite for Inn combat restriction (10-minute cooldown)"""
    
    def test_user_can_access_inn_when_not_in_combat(self, user_service, setup_test_user):
        """User with no recent activity can access Inn"""
        user_id = setup_test_user
        
        # User has no last_activity, should be allowed
        assert not user_service.is_in_combat(user_id)
    
    def test_user_cannot_access_inn_during_active_combat(self, user_service, setup_test_user):
        """User with recent activity (< 10 min) cannot access Inn"""
        user_id = setup_test_user
        
        # Simulate recent combat activity (5 minutes ago)
        user_service.track_activity(user_id)
        
        # Should be in combat
        assert user_service.is_in_combat(user_id)
    
    def test_user_can_access_inn_after_10_minute_cooldown(self, user_service, setup_test_user):
        """User can access Inn after 10 minutes of inactivity"""
        user_id = setup_test_user
        
        # Set last_activity to 11 minutes ago
        db = Database()
        session = db.get_session()
        try:
            user = session.query(Utente).filter_by(id_telegram=user_id).first()
            user.last_activity = datetime.datetime.now() - datetime.timedelta(minutes=11)
            session.commit()
        finally:
            session.close()
        
        # Should NOT be in combat
        assert not user_service.is_in_combat(user_id)
    
    def test_combat_actions_reset_cooldown_timer(self, user_service, setup_test_user):
        """Combat actions reset the 10-minute cooldown"""
        user_id = setup_test_user
        
        # Set initial activity 9 minutes ago
        db = Database()
        session = db.get_session()
        try:
            user = session.query(Utente).filter_by(id_telegram=user_id).first()
            user.last_activity = datetime.datetime.now() - datetime.timedelta(minutes=9)
            session.commit()
        finally:
            session.close()
        
        # Should be in combat
        assert user_service.is_in_combat(user_id)
        
        # New combat action resets timer
        user_service.track_activity(user_id)
        
        # Still in combat (timer reset)
        assert user_service.is_in_combat(user_id)
    
    def test_exactly_10_minutes_boundary(self, user_service, setup_test_user):
        """Test boundary condition at exactly 10 minutes"""
        user_id = setup_test_user
        
        # Set last_activity to exactly 10 minutes ago
        db = Database()
        session = db.get_session()
        try:
            user = session.query(Utente).filter_by(id_telegram=user_id).first()
            user.last_activity = datetime.datetime.now() - datetime.timedelta(minutes=10, seconds=1)
            session.commit()
        finally:
            session.close()
        
        # Should NOT be in combat (10 minutes have passed)
        assert not user_service.is_in_combat(user_id)

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
