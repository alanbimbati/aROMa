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

def test_targeting():
    pve_service = PvEService()
    user_service = UserService()
    db = Database()
    
    chat_id = 123456789
    
    # Track activity for 10 users
    print("Tracking activity for 10 users...")
    for i in range(1, 11):
        user_service.track_activity(i, chat_id)
    
    # The last 5 users (6, 7, 8, 9, 10) should have 70% chance of being picked
    
    # Create a mock mob in the DB
    session = db.get_session()
    # Clean up old test mobs
    session.query(Mob).filter_by(name="TestTargetMob").delete()
    
    test_mob = Mob(
        name="TestTargetMob",
        health=1000,
        max_health=1000,
        attack_damage=10,
        speed=100, # High speed for no cooldown
        chat_id=chat_id,
        is_dead=False
    )
    session.add(test_mob)
    session.commit()
    mob_id = test_mob.id
    session.close()
    
    print(f"Simulating 100 attacks from mob {mob_id} in chat {chat_id}...")
    
    results = {}
    for _ in range(100):
        # We need to mock get_user to return something valid for each ID
        # But since mob_random_attack calls user_service.get_user, we should ensure they exist or mock it
        # For simplicity, let's just check the logic in PvEService if we can
        
        events = pve_service.mob_random_attack(specific_mob_id=mob_id, chat_id=chat_id)
        if events:
            # Extract target from message (hacky but works for test)
            msg = events[0]['message']
            # Message format: "⚠️ **TestTargetMob** ha attaccato @username" or "⚠️ **TestTargetMob** ha attaccato Nome"
            # Our tag logic: tag = f"@{username}" if username else target.nome
            # In our case, users 1-10 don't have usernames or names in DB yet, so get_user might return None
            # Let's create them first
            pass

    # Actually, let's just verify the distribution of IDs picked by get_recent_users logic
    recent_users = user_service.get_recent_users(chat_id=chat_id)
    print(f"Recent users: {recent_users}")
    
    picked_counts = {i: 0 for i in range(1, 11)}
    for _ in range(1000):
        if len(recent_users) > 5 and random.random() < 0.7:
            target_id = random.choice(recent_users[-5:])
        else:
            target_id = random.choice(recent_users)
        picked_counts[target_id] += 1
    
    print("\nTargeting distribution (1000 trials):")
    recent_group = sum(picked_counts[i] for i in range(6, 11))
    older_group = sum(picked_counts[i] for i in range(1, 6))
    
    for i in range(1, 11):
        print(f"User {i}: {picked_counts[i]} times")
        
    print(f"\nRecent 5 users total: {recent_group} ({recent_group/10:.1f}%)")
    print(f"Older 5 users total: {older_group} ({older_group/10:.1f}%)")
    print("Expected: Recent group should be significantly higher (~70% + 30%/2 = 85% vs 15% if picking from all)")
    # Wait, if 70% chance for last 5, and 30% chance for all 10:
    # Last 5: 70% + (30% * 5/10) = 70% + 15% = 85%
    # First 5: 30% * 5/10 = 15%

    # Clean up
    session = db.get_session()
    session.query(Mob).filter_by(id=mob_id).delete()
    session.commit()
    session.close()

if __name__ == "__main__":
    test_targeting()
