import os
import sys
import datetime
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Add project root to path
sys.path.append(os.getcwd())

from models.user import Utente
from database import Database, Base

# Setup test DB
db = Database()
session = db.get_session()

def test_antispam_logic(user_id):
    user = session.query(Utente).filter_by(id_telegram=user_id).first()
    if not user:
        print(f"User {user_id} not found.")
        return

    print(f"Testing anti-spam for user: {user.nome} (ID: {user_id})")
    
    # Reset last_chat_drop_time
    user.last_chat_drop_time = None
    session.commit()
    
    # Simulate first message (should allow drop)
    now = datetime.datetime.now()
    print(f"First message at: {now}")
    
    # Logic check (simulated)
    def can_receive_reward(u):
        if not u.last_chat_drop_time:
            return True
        elapsed = (datetime.datetime.now() - u.last_chat_drop_time).total_seconds()
        return elapsed >= 30

    if can_receive_reward(user):
        print("✅ First reward allowed.")
        user.last_chat_drop_time = datetime.datetime.now()
        session.commit()
    else:
        print("❌ First reward blocked (Error!)")

    # Simulate second message immediately (should be blocked)
    print(f"Second message immediately after...")
    if not can_receive_reward(user):
        print("✅ Second reward blocked as expected.")
    else:
        print("❌ Second reward allowed (Error!)")

    # Simulate third message after 31 seconds (should be allowed)
    print(f"Simulating 31 seconds wait...")
    user.last_chat_drop_time = datetime.datetime.now() - datetime.timedelta(seconds=31)
    session.commit()
    
    if can_receive_reward(user):
        print("✅ Reward allowed after 31 seconds as expected.")
    else:
        print("❌ Reward blocked after 31 seconds (Error!)")

if __name__ == "__main__":
    # Use a known user ID from the DB or create a dummy one
    # For safety, let's just check the logic with a dummy object if we don't want to touch the DB
    # But since it's a test script, we can use a real one or a mock.
    
    # Mocking for pure logic test
    class MockUser:
        def __init__(self):
            self.last_chat_drop_time = None

    user = MockUser()
    
    def can_receive_reward(u):
        if not u.last_chat_drop_time:
            return True
        elapsed = (datetime.datetime.now() - u.last_chat_drop_time).total_seconds()
        return elapsed >= 30

    print("--- Logic Test ---")
    if can_receive_reward(user):
        print("✅ First reward allowed.")
        user.last_chat_drop_time = datetime.datetime.now()
    
    if not can_receive_reward(user):
        print("✅ Immediate second reward blocked.")
    
    user.last_chat_drop_time = datetime.datetime.now() - datetime.timedelta(seconds=31)
    if can_receive_reward(user):
        print("✅ Reward allowed after 31s.")
    
    print("\n--- DB Integration Test ---")
    # Try to find a real user to verify DB column works
    test_user = session.query(Utente).first()
    if test_user:
        test_antispam_logic(test_user.id_telegram)
    else:
        print("No users found in DB to test integration.")
    
    session.close()
