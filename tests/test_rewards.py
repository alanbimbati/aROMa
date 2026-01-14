import sys
import os
sys.path.append(os.getcwd())

from services.user_service import UserService
from database import Database
from models.user import Utente

def test_rewards():
    user_service = UserService()
    db = Database()
    session = db.get_session()
    
    # Get a test user
    user = session.query(Utente).first()
    if not user:
        print("No user found in database for testing.")
        return
    
    initial_exp = user.exp
    initial_points = user.points
    test_id = user.id_telegram
    
    print(f"Testing rewards for user {test_id} ({user.username})")
    print(f"Initial: EXP={initial_exp}, Points={initial_points}")
    
    # Test add_exp_by_id
    user_service.add_exp_by_id(test_id, 50)
    
    # Test add_points_by_id
    user_service.add_points_by_id(test_id, 100)
    
    # Refresh user
    session.expire_all()
    user = session.query(Utente).filter_by(id_telegram=test_id).first()
    
    print(f"After rewards: EXP={user.exp}, Points={user.points}")
    
    if user.exp == initial_exp + 50 and user.points == initial_points + 100:
        print("✅ Reward verification SUCCESS")
    else:
        print("❌ Reward verification FAILED")
    
    session.close()

if __name__ == "__main__":
    test_rewards()
