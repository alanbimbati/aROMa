"""
Test Helpers
Common utility functions for test setup and teardown
"""

def cleanup_test_user(session, user_id):
    """
    Clean up all related data for a test user before deletion
    This ensures no foreign key violations occur during tearDown
    """
    from models.dungeon import DungeonParticipant
    from models.resources import UserResource
    from models.user import Utente
    
    # Order matters: clean up child tables first
    session.query(DungeonParticipant).filter_by(user_id=user_id).delete()
    session.query(UserResource).filter_by(user_id=user_id).delete()
    # Add more cleanup as needed for other FK relationships
    
    # Finally delete the user
    session.query(Utente).filter_by(id_telegram=user_id).delete()
    session.commit()
