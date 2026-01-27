import os
import sys
import json

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import Database
from services.event_dispatcher import EventDispatcher
from services.achievement_tracker import AchievementTracker
from models.stats import UserStat
from models.achievements import UserAchievement

def verify():
    db = Database()
    event_dispatcher = EventDispatcher()
    tracker = AchievementTracker()
    
    # Use a dummy user ID
    user_id = 999999999
    
    print(f"--- Verifying Achievement Logic for User {user_id} ---")
    
    # 1. Log One-Shot Event
    print("Logging damage_dealt event with is_one_shot=True...")
    event_dispatcher.log_event(
        event_type='damage_dealt',
        user_id=user_id,
        value=100,
        context={'is_one_shot': True, 'mob_name': 'Test Mob'}
    )
    
    # 2. Log Level-Up Event
    print("Logging level_up event with value=10...")
    event_dispatcher.log_event(
        event_type='level_up',
        user_id=user_id,
        value=10,
        context={'exp': 1000}
    )
    
    # 3. Log Damage Taken Event (Scudo Vivente)
    print("Logging damage_taken event with value=500...")
    event_dispatcher.log_event(
        event_type='damage_taken',
        user_id=user_id,
        value=500,
        context={'mob_name': 'Test Mob'}
    )
    
    # 4. Process Events
    print("Processing pending events...")
    tracker.process_pending_events()
    
    # 5. Check Stats
    session = db.get_session()
    try:
        one_shots_stat = session.query(UserStat).filter_by(user_id=user_id, stat_key='one_shots').first()
        level_stat = session.query(UserStat).filter_by(user_id=user_id, stat_key='level').first()
        damage_taken_stat = session.query(UserStat).filter_by(user_id=user_id, stat_key='total_damage_taken').first()
        
        print(f"Stat 'one_shots': {one_shots_stat.value if one_shots_stat else 'NOT FOUND'}")
        print(f"Stat 'level': {level_stat.value if level_stat else 'NOT FOUND'}")
        print(f"Stat 'total_damage_taken': {damage_taken_stat.value if damage_taken_stat else 'NOT FOUND'}")
        
        # 6. Check Achievements
        one_shot_ach = session.query(UserAchievement).filter_by(user_id=user_id, achievement_key='one_shot_one_kill').first()
        level_ach = session.query(UserAchievement).filter_by(user_id=user_id, achievement_key='level_master').first()
        scudo_ach = session.query(UserAchievement).filter_by(user_id=user_id, achievement_key='tank').first()
        
        print(f"Achievement 'one_shot_one_kill' progress: {one_shot_ach.progress_value if one_shot_ach else 'NOT FOUND'}")
        print(f"Achievement 'level_master' progress: {level_ach.progress_value if level_ach else 'NOT FOUND'}")
        print(f"Achievement 'tank' (Scudo Vivente) progress: {scudo_ach.progress_value if scudo_ach else 'NOT FOUND'}")
        
        if (one_shots_stat and one_shots_stat.value >= 1 and 
            level_stat and level_stat.value == 10 and 
            damage_taken_stat and damage_taken_stat.value == 500):
            print("\n✅ VERIFICATION SUCCESSFUL!")
        else:
            print("\n❌ VERIFICATION FAILED!")
            
    finally:
        # Cleanup dummy data
        session.query(UserStat).filter_by(user_id=user_id).delete()
        session.query(UserAchievement).filter_by(user_id=user_id).delete()
        # Note: GameEvents are marked as processed, we can leave them or delete if we want to be thorough
        session.commit()
        session.close()

if __name__ == "__main__":
    verify()
