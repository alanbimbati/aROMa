from database import Database
from services.user_service import UserService
from services.drop_service import DropService
from models.user import Utente
import datetime

def verify_invincible():
    print("Initializing Database...")
    db = Database()
    us = UserService()
    ds = DropService()
    session = db.get_session()
    
    # Create test user
    user_id = 777777
    session.query(Utente).filter_by(id_telegram=user_id).delete()
    session.commit()
    
    u = Utente(id_telegram=user_id, username="InvincibleTester", nome="Tester")
    session.add(u)
    session.commit()
    
    # Test 1: Not Invincible
    print("--- Test 1: Not Invincible ---")
    is_inv = us.is_invincible(u)
    print(f"Is Invincible? {is_inv} (Expected: False)")
    
    if is_inv:
        print("❌ Failed Test 1")
    else:
        print("✅ Test 1 Passed")
        
    # Test 2: Invincible
    print("--- Test 2: Invincible ---")
    u.invincible_until = datetime.datetime.now() + datetime.timedelta(minutes=5)
    session.commit()
    
    # Refresh object
    session.refresh(u)
    is_inv = us.is_invincible(u)
    print(f"Is Invincible? {is_inv} (Expected: True)")
    
    if is_inv:
        print("✅ Test 2 Passed")
    else:
        print("❌ Failed Test 2")
        
    # Test 3: DropService Call
    print("--- Test 3: DropService Call ---")
    try:
        # Mock message/bot not needed for this specific check if we call internal logic or just verify method existence
        # But let's verify DropService has access
        ds.user_service.is_invincible(u)
        print("✅ DropService can call is_invincible")
    except AttributeError:
        print("❌ DropService still raises AttributeError")
    except Exception as e:
        print(f"❌ Other error: {e}")
        
    session.close()

if __name__ == "__main__":
    verify_invincible()
