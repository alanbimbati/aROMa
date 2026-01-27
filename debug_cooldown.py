import os
import sys
import datetime

# Add project root to path
sys.path.append(os.getcwd())

from database import Database
from models.user import Utente

def check_user_cooldown(user_id):
    db = Database()
    session = db.get_session()
    user = session.query(Utente).filter_by(id_telegram=user_id).first()
    
    if not user:
        print(f"User {user_id} not found.")
        return
    
    print(f"User: {user.nome} ({user.id_telegram})")
    print(f"Speed: {user.speed}")
    print(f"Last Attack Time: {user.last_attack_time}")
    
    if user.last_attack_time:
        now = datetime.datetime.now()
        elapsed = (now - user.last_attack_time).total_seconds()
        print(f"Current Time: {now}")
        print(f"Elapsed Seconds: {elapsed}")
        
        user_speed = user.speed or 0
        cooldown_seconds = 60 / (1 + user_speed * 0.01)
        print(f"Required Cooldown: {cooldown_seconds}s")
        
        if elapsed < cooldown_seconds:
            print(f"COOLDOWN ACTIVE: {int(cooldown_seconds - elapsed)}s remaining")
        else:
            print("COOLDOWN EXPIRED")
    else:
        print("No last attack time recorded.")
    
    session.close()

if __name__ == "__main__":
    # Use a real user ID from the logs if possible, or just check a few
    # The user reported this, so I'll check their ID if I can find it.
    # From previous logs, I saw 62716473 (hardcoded fallback) and others.
    # I'll check the user who reported the error if I can.
    # The user didn't provide their ID, but I can check the database for recent activity.
    check_user_cooldown(62716473)
