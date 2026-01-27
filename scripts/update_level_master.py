from database import Database
from models.achievements import Achievement
import sys
import json

def update_level_master():
    print("Updating 'Maestro del Livello' achievement...")
    db = Database()
    session = db.get_session()
    
    try:
        ach = session.query(Achievement).filter_by(achievement_key='level_master').first()
        if ach:
            print("Found achievement. Updating tiers...")
            # User req: Gold=80, Diamond=100. Wumpa rewards.
            ach.tiers = json.dumps({
                "bronze": {"threshold": 10, "rewards": {"points": 200, "title": "Promessa"}},
                "silver": {"threshold": 40, "rewards": {"points": 500, "title": "Veterano"}},
                "gold": {"threshold": 80, "rewards": {"points": 1000, "title": "Eroe"}},
                "platinum": {"threshold": 90, "rewards": {"points": 2000, "title": "Leggenda"}},
                "diamond": {"threshold": 100, "rewards": {"points": 5000, "title": "Semidio"}},
                "legendary": {"threshold": 120, "rewards": {"points": 10000, "title": "Divinità"}}
            })
            session.commit()
            print("Achievement updated successfully.")
        else:
            print("Achievement 'level_master' not found.")
            
    except Exception as e:
        print(f"Error: {e}")
        session.rollback()
    finally:
        session.close()

if __name__ == "__main__":
    update_level_master()
