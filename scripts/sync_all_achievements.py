from database import Database
from models.achievements import Achievement
import sys
import json

def sync_achievements():
    print("Syncing ALL achievements to current DB...")
    db = Database()
    session = db.get_session()
    
    achievements_data = [
        # --- Resting Achievements ---
        {
            "key": "dormiglione",
            "name": "🛌 Dormiglione",
            "description": "Passa del tempo a riposare nella locanda (minuti)",
            "stat_key": "minutes_rested_inn",
            "category": "classici",
            "tiers": {
                "bronze": {"threshold": 1000, "rewards": {"points": 500}},
                "silver": {"threshold": 5000, "rewards": {"points": 1000}},
                "gold": {"threshold": 10000, "rewards": {"points": 2000}},
                "platinum": {"threshold": 20000, "rewards": {"points": 5000, "title": "Dormiglione"}},
                "diamond": {"threshold": 50000, "rewards": {"points": 10000}},
                "legendary": {"threshold": 100000, "rewards": {"points": 20000}}
            }
        },
        {
            "key": "vita_nuova",
            "name": "❤️ Vita Nuova",
            "description": "Ripristina Punti Vita riposando nella locanda",
            "stat_key": "hp_restored_inn",
            "category": "classici",
            "tiers": {
                "bronze": {"threshold": 500, "rewards": {"points": 200}},
                "silver": {"threshold": 2500, "rewards": {"points": 500}},
                "gold": {"threshold": 5000, "rewards": {"points": 1000}},
                "platinum": {"threshold": 10000, "rewards": {"points": 2000, "title": "Immortale"}},
                "diamond": {"threshold": 25000, "rewards": {"points": 5000}},
                "legendary": {"threshold": 50000, "rewards": {"points": 10000}}
            }
        },
        {
            "key": "mente_libera",
            "name": "🧠 Mente Libera",
            "description": "Ripristina Punti Mana riposando nella locanda",
            "stat_key": "mana_restored_inn",
            "category": "classici",
            "tiers": {
                "bronze": {"threshold": 500, "rewards": {"points": 200}},
                "silver": {"threshold": 2500, "rewards": {"points": 500}},
                "gold": {"threshold": 5000, "rewards": {"points": 1000}},
                "platinum": {"threshold": 10000, "rewards": {"points": 2000, "title": "Guru"}},
                "diamond": {"threshold": 25000, "rewards": {"points": 5000}},
                "legendary": {"threshold": 50000, "rewards": {"points": 10000}}
            }
        },
        {
            "key": "sonno_leggero",
            "name": "🥱 Sonno Leggero",
            "description": "Riposa recuperando almeno 10 HP",
            "stat_key": "rest_sessions_10hp",
            "category": "classici",
            "tiers": {
                "bronze": {"threshold": 10, "rewards": {"points": 100}},
                "silver": {"threshold": 50, "rewards": {"points": 300}},
                "gold": {"threshold": 100, "rewards": {"points": 500}},
                "platinum": {"threshold": 200, "rewards": {"points": 1000, "title": "Sonnellino"}},
                "diamond": {"threshold": 500, "rewards": {"points": 2000}},
                "legendary": {"threshold": 1000, "rewards": {"points": 5000}}
            }
        },
        # --- Level Master Achievement ---
        {
            "key": "level_master",
            "name": "🆙 Maestro del Livello",
            "description": "Raggiungi nuove vette di potere.",
            "stat_key": "level", # Assuming this is the key, verified in previous step
            "category": "classici",
            "tiers": {
                "bronze": {"threshold": 10, "rewards": {"points": 200, "title": "Promessa"}},
                "silver": {"threshold": 40, "rewards": {"points": 500, "title": "Veterano"}},
                "gold": {"threshold": 80, "rewards": {"points": 1000, "title": "Eroe"}},
                "platinum": {"threshold": 90, "rewards": {"points": 2000, "title": "Leggenda"}},
                "diamond": {"threshold": 100, "rewards": {"points": 5000, "title": "Semidio"}},
                "legendary": {"threshold": 120, "rewards": {"points": 10000, "title": "Divinità"}}
            }
        }
    ]
    
    try:
        count = 0
        for data in achievements_data:
            ach = session.query(Achievement).filter_by(achievement_key=data['key']).first()
            if not ach:
                print(f"Creating {data['name']}...")
                ach = Achievement(
                    achievement_key=data['key'],
                    name=data['name'],
                    description=data['description'],
                    stat_key=data['stat_key'],
                    category=data['category'],
                    tiers=json.dumps(data['tiers'])
                )
                session.add(ach)
                count += 1
            else:
                print(f"Updating {data['name']}...")
                ach.name = data['name']
                ach.description = data['description']
                ach.stat_key = data['stat_key']
                ach.category = data['category']
                ach.tiers = json.dumps(data['tiers'])
                count += 1
                
        session.commit()
        print(f"Synced {count} achievements successfully.")
    except Exception as e:
        print(f"Error: {e}")
        session.rollback()
    finally:
        session.close()

if __name__ == "__main__":
    sync_achievements()
