import sys
import datetime
import traceback
from database import Database
from models.seasons import Season

def test_season():
    try:
        db = Database()
        session = db.get_session()
        
        now = datetime.datetime.now()
        print(f"Current System Time: {now} (Naive)")
        
        all_seasons = session.query(Season).all()
        print(f"Total seasons in DB: {len(all_seasons)}")
        for s in all_seasons:
            print(f"\n--- Season: {s.name} ---")
            print(f"ID: {s.id}")
            print(f"Active Flag: {s.is_active}")
            print(f"Start: {s.start_date} (Type: {type(s.start_date)})")
            print(f"End:   {s.end_date} (Type: {type(s.end_date)})")
            
            c1 = s.is_active == True
            c2 = s.start_date <= now
            c3 = s.end_date >= now
            
            print(f"Comparison: is_active==True: {c1}")
            print(f"Comparison: start <= now: {c2}")
            print(f"Comparison: end >= now: {c3}")
            
            if c1 and c2 and c3:
                print(">> SEASON IS VALID <<")
            else:
                print(">> SEASON IS NOT VALID <<")
            
    except Exception as e:
        traceback.print_exc()

if __name__ == "__main__":
    test_season()
