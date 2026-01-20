import csv
import json
import sys
import os
from database import Database
from models.achievements import Achievement

def load_achievements_from_csv(csv_path="data/achievements.csv"):
    print(f"Loading achievements from {csv_path}...")
    
    if not os.path.exists(csv_path):
        print(f"Error: File {csv_path} not found.")
        return

    db = Database()
    session = db.get_session()
    
    try:
        with open(csv_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            count = 0
            for row in reader:
                key = row['key']
                name = row['name']
                description = row['description']
                stat_key = row['stat_key']
                category = row['category']
                tiers_str = row['tiers']
                
                # Validate JSON
                try:
                    json.loads(tiers_str)
                except json.JSONDecodeError as e:
                    print(f"Error parsing JSON for {key}: {e}")
                    continue

                ach = session.query(Achievement).filter_by(achievement_key=key).first()
                if not ach:
                    print(f"Creating {name}...")
                    ach = Achievement(
                        achievement_key=key,
                        name=name,
                        description=description,
                        stat_key=stat_key,
                        category=category,
                        tiers=tiers_str
                    )
                    session.add(ach)
                else:
                    print(f"Updating {name}...")
                    ach.name = name
                    ach.description = description
                    ach.stat_key = stat_key
                    ach.category = category
                    ach.tiers = tiers_str
                
                count += 1
            
            session.commit()
            print(f"Successfully processed {count} achievements.")
            
    except Exception as e:
        print(f"Error: {e}")
        session.rollback()
    finally:
        session.close()

if __name__ == "__main__":
    path = "data/achievements.csv"
    if len(sys.argv) > 1:
        path = sys.argv[1]
    load_achievements_from_csv(path)
