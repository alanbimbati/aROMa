from database import Database
from models.achievements import Achievement
import sys
import json

def update_resting_achievements():
    print("Updating resting achievements...")
    db = Database()
    session = db.get_session()
    
    try:
        # 1. Update Dormiglione (Time)
        dorm = session.query(Achievement).filter_by(achievement_key='dormiglione').first()
        if dorm:
            print("Updating Dormiglione to track Time...")
            dorm.description = "Passa del tempo a riposare nella locanda (minuti)"
            dorm.stat_key = "minutes_rested_inn"
            dorm.category = "classici"
            # Tiers: 1h, 5h, 10h, 20h, 50h (in minutes)
            dorm.tiers = json.dumps({
                "bronze": {"threshold": 60, "rewards": {"points": 100}},      # 1h
                "silver": {"threshold": 300, "rewards": {"points": 500}},     # 5h
                "gold": {"threshold": 600, "rewards": {"points": 1000}},     # 10h
                "platinum": {"threshold": 1200, "rewards": {"points": 2000, "title": "Dormiglione"}}, # 20h
                "diamond": {"threshold": 3000, "rewards": {"points": 5000}},  # 50h
                "legendary": {"threshold": 6000, "rewards": {"points": 10000}} # 100h
            })
        
        # 2. Create Vita Nuova (HP)
        hp_ach = session.query(Achievement).filter_by(achievement_key='vita_nuova').first()
        if not hp_ach:
            print("Creating 'Vita Nuova' achievement...")
            hp_ach = Achievement(
                achievement_key='vita_nuova',
                name='Vita Nuova',
                description='Ripristina Punti Vita riposando nella locanda',
                stat_key='hp_restored_inn',
                category='classici',
                tiers=json.dumps({
                    "bronze": {"threshold": 1000, "rewards": {"points": 100}},
                    "silver": {"threshold": 5000, "rewards": {"points": 500}},
                    "gold": {"threshold": 10000, "rewards": {"points": 1000}},
                    "platinum": {"threshold": 20000, "rewards": {"points": 2000, "title": "Immortale"}},
                    "diamond": {"threshold": 50000, "rewards": {"points": 5000}},
                    "legendary": {"threshold": 100000, "rewards": {"points": 10000}}
                })
            )
            session.add(hp_ach)
            
        # 3. Create Mente Libera (Mana)
        mana_ach = session.query(Achievement).filter_by(achievement_key='mente_libera').first()
        if not mana_ach:
            print("Creating 'Mente Libera' achievement...")
            mana_ach = Achievement(
                achievement_key='mente_libera',
                name='Mente Libera',
                description='Ripristina Punti Mana riposando nella locanda',
                stat_key='mana_restored_inn',
                category='classici',
                tiers=json.dumps({
                    "bronze": {"threshold": 1000, "rewards": {"points": 100}},
                    "silver": {"threshold": 5000, "rewards": {"points": 500}},
                    "gold": {"threshold": 10000, "rewards": {"points": 1000}},
                    "platinum": {"threshold": 20000, "rewards": {"points": 2000, "title": "Guru"}},
                    "diamond": {"threshold": 50000, "rewards": {"points": 5000}},
                    "legendary": {"threshold": 100000, "rewards": {"points": 10000}}
                })
            )
            session.add(mana_ach)
            
        session.commit()
        print("Achievements updated successfully.")
    except Exception as e:
        print(f"Error: {e}")
        session.rollback()
    finally:
        session.close()

if __name__ == "__main__":
    update_resting_achievements()
