import datetime
from database import Database
from models.seasons import Season, SeasonProgress
from services.season_manager import SeasonManager

def verify_season_refactor():
    db = Database()
    session = db.get_session()
    manager = SeasonManager()
    
    user_id = 999999  # Test user
    
    try:
        # 1. Ensure an active season exists
        season = manager.get_active_season()
        if not season:
            print("Creating test season...")
            season = Season(
                name="Test Season",
                start_date=datetime.datetime.now() - datetime.timedelta(days=1),
                end_date=datetime.datetime.now() + datetime.timedelta(days=1),
                is_active=True,
                exp_multiplier=1.0
            )
            session.add(season)
            session.commit()
            session.refresh(season)
        
        print(f"Active Season: {season.name}")
        
        # 2. Test EXP addition and Rank Cap with Dynamic Curve
        print("\nTesting EXP addition and Rank Cap...")
        
        # Reset progress for test user to Rank 1
        progress = session.query(SeasonProgress).filter_by(user_id=user_id, season_id=season.id).first()
        if progress:
            progress.current_level = 1
            progress.current_exp = 0
            session.commit()
        else:
            progress = SeasonProgress(user_id=user_id, season_id=season.id, current_level=1, current_exp=0)
            session.add(progress)
            session.commit()
            
        print(f"Initial Rank: {progress.current_level}")
        
        # Rank 1 -> 2 requires 100 * (1^2) = 100 EXP
        print("Adding 50 EXP (Should not level up)...")
        manager.add_seasonal_exp(user_id, 50)
        session.refresh(progress)
        print(f"Rank: {progress.current_level}, EXP: {progress.current_exp} (Expected: 1, 50)")
        
        print("Adding 60 EXP (Should level up to 2)...")
        # 50 + 60 = 110. Req = 100. New EXP = 10. Rank = 2.
        manager.add_seasonal_exp(user_id, 60)
        session.refresh(progress)
        print(f"Rank: {progress.current_level}, EXP: {progress.current_exp} (Expected: 2, 10)")
        
        # Rank 2 -> 3 requires 100 * (2^2) = 400 EXP
        print("Adding 390 EXP (Should level up to 3)...")
        # 10 + 390 = 400. Req = 400. New EXP = 0. Rank = 3.
        manager.add_seasonal_exp(user_id, 390)
        session.refresh(progress)
        print(f"Rank: {progress.current_level}, EXP: {progress.current_exp} (Expected: 3, 0)")
        
        # Test Cap
        print("\nTesting Cap...")
        progress.current_level = 99
        progress.current_exp = 0
        session.commit()
        
        # Rank 99 -> 100 requires 100 * (99^2) = 980100 EXP
        req_99 = 100 * (99**2)
        print(f"Adding {req_99} EXP to reach cap...")
        manager.add_seasonal_exp(user_id, req_99)
        session.refresh(progress)
        print(f"Rank after cap reach: {progress.current_level} (Expected: 100)")
        print(f"EXP after cap reach: {progress.current_exp} (Expected: 0)")
        
        if progress.current_level == 100 and progress.current_exp == 0:
            print("\n✅ Rank Cap Verification Passed!")
        else:
            print("\n❌ Rank Cap Verification Failed!")
            
    finally:
        session.close()

if __name__ == "__main__":
    verify_season_refactor()
