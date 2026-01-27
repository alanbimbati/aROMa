import sys
import os
import random
import datetime

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from services.pve_service import PvEService
from services.user_service import UserService
from database import Database
from models.pve import Mob
from models.user import Utente

def test_multiple_spawns():
    pve_service = PvEService()
    db = Database()
    
    chat_id = 999888777
    
    print(f"Testing multiple spawns in chat {chat_id}...")
    
    # Clean up old test mobs
    session = db.get_session()
    session.query(Mob).filter_by(chat_id=chat_id).delete()
    session.commit()
    session.close()
    
    # Create a test user in the DB
    session = db.get_session()
    test_user = session.query(Utente).filter_by(id_telegram=15001).first()
    if not test_user:
        test_user = Utente(id_telegram=15001, nome="TestUser", username="testuser")
        session.add(test_user)
        session.commit()
    session.close()

    # Track activity for a test user
    pve_service.user_service.track_activity(15001, chat_id)
    
    # Spawn 3 mobs
    for i in range(3):
        mob_id, attack_events = pve_service.spawn_daily_mob(chat_id=chat_id)
        if mob_id:
            print(f"Spawned mob {i+1} with ID {mob_id}")
            if attack_events:
                print(f"Mob {i+1} attacked immediately: {attack_events[0]['message']}")
            else:
                print(f"ERROR: Mob {i+1} did NOT attack immediately!")
        else:
            print(f"ERROR: Failed to spawn mob {i+1}")

    # Verify count in DB
    session = db.get_session()
    count = session.query(Mob).filter_by(chat_id=chat_id, is_dead=False).count()
    print(f"Total active mobs in chat {chat_id}: {count}")
    
    if count == 3:
        print("SUCCESS: Multiple mobs spawned correctly.")
    else:
        print(f"FAILURE: Expected 3 mobs, found {count}.")

    # Clean up
    session.query(Mob).filter_by(chat_id=chat_id).delete()
    session.commit()
    session.close()

if __name__ == "__main__":
    test_multiple_spawns()
