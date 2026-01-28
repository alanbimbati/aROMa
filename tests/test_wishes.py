import os
import sys
sys.path.append(os.getcwd())

from services.wish_service import WishService
from services.user_service import UserService
from database import Database
from models.user import Utente
import random

def test_wishes():
    print("🧪 Testing Dragon Ball Wishes")
    os.environ['TEST_DB'] = '1'
    
    db = Database()
    user_service = UserService()
    wish_service = WishService()
    
    session = db.get_session()
    
    # Create a test user with None stats
    test_user_id = 123456789
    
    # Cleanup any leftover data from previous failed runs
    from models.achievements import GameEvent
    from models.stats import UserStat
    session.query(GameEvent).filter_by(user_id=test_user_id).delete()
    session.query(UserStat).filter_by(user_id=test_user_id).delete()
    
    user = session.query(Utente).filter_by(id_telegram=test_user_id).first()
    if user:
        session.delete(user)
    session.commit()
        
    user = Utente(id_telegram=test_user_id, nome="Test User", exp=None, points=None, livello=1)
    session.add(user)
    session.commit()
    
    print(f"User created with exp=None, points=None")
    
    # Test Shenron Wumpa Wish
    print("Testing Shenron Wumpa wish...")
    msg = wish_service.grant_wish(user, "wumpa", "Shenron")
    print(f"  Result: {msg}")
    
    # Verify points added
    session.expire_all()
    user = session.query(Utente).filter_by(id_telegram=test_user_id).first()
    print(f"  User points: {user.points}")
    assert user.points is not None and user.points > 0
    
    # Test Shenron EXP Wish
    print("Testing Shenron EXP wish...")
    msg = wish_service.grant_wish(user, "exp", "Shenron")
    print(f"  Result: {msg}")
    
    # Verify exp added
    session.expire_all()
    user = session.query(Utente).filter_by(id_telegram=test_user_id).first()
    print(f"  User exp: {user.exp}")
    assert user.exp is not None and user.exp > 0
    
    # Test Porunga Wumpa Wish
    print("Testing Porunga Wumpa wish...")
    msg = wish_service.grant_porunga_wish(user, "wumpa", 1)
    print(f"  Result: {msg}")
    
    # Cleanup
    session.query(GameEvent).filter_by(user_id=test_user_id).delete()
    session.query(UserStat).filter_by(user_id=test_user_id).delete()
    session.delete(user)
    session.commit()
    session.close()
    
    print("✅ All wish tests passed!")

if __name__ == "__main__":
    test_wishes()
