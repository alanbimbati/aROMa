from database import Database
from services.user_service import UserService
from models.user import Utente

def verify_profile_fix():
    print("Initializing Database...")
    db = Database()
    us = UserService()
    session = db.get_session()
    
    # Create test user
    user_id = 888888
    session.query(Utente).filter_by(id_telegram=user_id).delete()
    session.commit()
    
    u = Utente(id_telegram=user_id, username="FatigueTester", nome="Tester", health=100, max_health=100, current_hp=100)
    session.add(u)
    session.commit()
    
    # Test 1: Not Fatigued (100% HP)
    print("--- Test 1: Not Fatigued ---")
    is_fatigued = us.check_fatigue(u)
    print(f"Is Fatigued? {is_fatigued} (Expected: False)")
    
    if is_fatigued:
        print("❌ Failed Test 1")
    else:
        print("✅ Test 1 Passed")
        
    # Test 2: Fatigued (10% HP)
    print("--- Test 2: Fatigued ---")
    u.current_hp = 10
    session.commit()
    
    # Refresh object
    session.refresh(u)
    is_fatigued = us.check_fatigue(u)
    print(f"Is Fatigued? {is_fatigued} (Expected: True)")
    
    if is_fatigued:
        print("✅ Test 2 Passed")
    else:
        print("❌ Failed Test 2")
        
    # Test 3: Resting Status (just to be sure it exists)
    print("--- Test 3: Resting Status ---")
    try:
        us.get_resting_status(user_id)
        print("✅ get_resting_status exists")
    except AttributeError:
        print("❌ get_resting_status missing")
        
    session.close()

if __name__ == "__main__":
    verify_profile_fix()
