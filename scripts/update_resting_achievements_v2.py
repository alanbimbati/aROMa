from database import Database
from models.achievements import Achievement
import sys
import json

def update_resting_achievements_v2():
    print("Refining resting achievements (v2)...")
    db = Database()
    session = db.get_session()
    
    try:
        # 1. Dormiglione (Time) - Start 1000 min
        dorm = session.query(Achievement).filter_by(achievement_key='dormiglione').first()
        if dorm:
            print("Updating Dormiglione...")
            dorm.name = "🛌 Dormiglione"
            dorm.description = "Passa del tempo a riposare nella locanda (minuti)"
            # Tiers: 1000, 5000, 10000, 20000, 50000
            dorm.tiers = json.dumps({
                "bronze": {"threshold": 1000, "rewards": {"points": 500}},
                "silver": {"threshold": 5000, "rewards": {"points": 1000}},
                "gold": {"threshold": 10000, "rewards": {"points": 2000}},
                "platinum": {"threshold": 20000, "rewards": {"points": 5000, "title": "Dormiglione"}},
                "diamond": {"threshold": 50000, "rewards": {"points": 10000}},
                "legendary": {"threshold": 100000, "rewards": {"points": 20000}}
            })
        
        # 2. Vita Nuova (HP) - Lower start (500)
        hp_ach = session.query(Achievement).filter_by(achievement_key='vita_nuova').first()
        if hp_ach:
            print("Updating Vita Nuova...")
            hp_ach.name = "❤️ Vita Nuova"
            # Tiers: 500, 2500, 5000, 10000, 25000
            hp_ach.tiers = json.dumps({
                "bronze": {"threshold": 500, "rewards": {"points": 200}},
                "silver": {"threshold": 2500, "rewards": {"points": 500}},
                "gold": {"threshold": 5000, "rewards": {"points": 1000}},
                "platinum": {"threshold": 10000, "rewards": {"points": 2000, "title": "Immortale"}},
                "diamond": {"threshold": 25000, "rewards": {"points": 5000}},
                "legendary": {"threshold": 50000, "rewards": {"points": 10000}}
            })
            
        # 3. Mente Libera (Mana) - Lower start (500)
        mana_ach = session.query(Achievement).filter_by(achievement_key='mente_libera').first()
        if mana_ach:
            print("Updating Mente Libera...")
            mana_ach.name = "🧠 Mente Libera"
            # Tiers: 500, 2500, 5000, 10000, 25000
            mana_ach.tiers = json.dumps({
                "bronze": {"threshold": 500, "rewards": {"points": 200}},
                "silver": {"threshold": 2500, "rewards": {"points": 500}},
                "gold": {"threshold": 5000, "rewards": {"points": 1000}},
                "platinum": {"threshold": 10000, "rewards": {"points": 2000, "title": "Guru"}},
                "diamond": {"threshold": 25000, "rewards": {"points": 5000}},
                "legendary": {"threshold": 50000, "rewards": {"points": 10000}}
            })
            
        # 4. Sonno Leggero (Count rests >= 10 HP)
        sonno = session.query(Achievement).filter_by(achievement_key='sonno_leggero').first()
        if not sonno:
            print("Creating 'Sonno Leggero' achievement...")
            sonno = Achievement(
                achievement_key='sonno_leggero',
                name='🥱 Sonno Leggero',
                description='Riposa recuperando almeno 10 HP',
                stat_key='rest_sessions_10hp',
                category='classici',
                tiers=json.dumps({
                    "bronze": {"threshold": 10, "rewards": {"points": 100}},
                    "silver": {"threshold": 50, "rewards": {"points": 300}},
                    "gold": {"threshold": 100, "rewards": {"points": 500}},
                    "platinum": {"threshold": 200, "rewards": {"points": 1000, "title": "Sonnellino"}},
                    "diamond": {"threshold": 500, "rewards": {"points": 2000}},
                    "legendary": {"threshold": 1000, "rewards": {"points": 5000}}
                })
            )
            session.add(sonno)
        else:
            print("Updating Sonno Leggero...")
            sonno.name = "🥱 Sonno Leggero"
            sonno.category = "classici"
            
        session.commit()
        print("Achievements updated successfully.")
    except Exception as e:
        print(f"Error: {e}")
        session.rollback()
    finally:
        session.close()

if __name__ == "__main__":
    update_resting_achievements_v2()
