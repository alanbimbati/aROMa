import sys
import os
import datetime

# Add parent directory to path to import modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from database import Database
from models.seasons import Season

def extend_season():
    print("Extending active season...")
    db = Database()
    session = db.get_session()
    
    try:
        now = datetime.datetime.now()
        active_season = session.query(Season).filter(
            Season.is_active == True,
            Season.start_date <= now,
            Season.end_date >= now
        ).first()
        
        if active_season:
            print(f"Found active season: {active_season.name}")
            print(f"Current end date: {active_season.end_date}")
            
            new_end_date = datetime.datetime(2026, 4, 30, 23, 59, 59)
            active_season.end_date = new_end_date
            
            session.commit()
            print(f"✅ Season extended to: {new_end_date}")
        else:
            print("❌ No active season found to extend.")
            
    except Exception as e:
        session.rollback()
        print(f"Error: {e}")
    finally:
        session.close()

if __name__ == "__main__":
    extend_season()
