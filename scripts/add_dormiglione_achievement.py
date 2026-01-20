from database import Database
from models.achievements import Achievement
import sys
import json

def add_dormiglione():
    print("Adding 'Dormiglione' achievement...")
    db = Database()
    session = db.get_session()
    
    try:
        # Check if exists
        exists = session.query(Achievement).filter_by(achievement_key='dormiglione').first()
        if exists:
            print("Achievement 'dormiglione' already exists.")
            return

        ach = Achievement(
            achievement_key='dormiglione',
            name='Dormiglione',
            description='Ripristina statistiche riposando nella locanda',
            stat_key='stats_restored_inn',
            category='social',
            tiers=json.dumps({
                "bronze": {"threshold": 1000, "rewards": {"points": 100}},
                "silver": {"threshold": 5000, "rewards": {"points": 500}},
                "gold": {"threshold": 10000, "rewards": {"points": 1000}},
                "platinum": {"threshold": 20000, "rewards": {"points": 2000, "title": "Dormiglione"}},
                "diamond": {"threshold": 50000, "rewards": {"points": 5000}},
                "legendary": {"threshold": 100000, "rewards": {"points": 10000}}
            })
        )
        session.add(ach)
        session.commit()
        print("Achievement 'Dormiglione' added successfully.")
    except Exception as e:
        print(f"Error: {e}")
        session.rollback()
    finally:
        session.close()

if __name__ == "__main__":
    add_dormiglione()
