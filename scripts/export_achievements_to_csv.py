import csv
import sys
import os
from database import Database
from models.achievements import Achievement

def export_achievements_to_csv(csv_path="data/achievements.csv"):
    print(f"Exporting ALL achievements to {csv_path}...")
    
    db = Database()
    session = db.get_session()
    
    try:
        achievements = session.query(Achievement).all()
        
        if not achievements:
            print("No achievements found in database.")
            return

        # Ensure directory exists
        os.makedirs(os.path.dirname(csv_path), exist_ok=True)
        
        with open(csv_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            # Write header
            writer.writerow(['key', 'name', 'description', 'stat_key', 'category', 'tiers'])
            
            count = 0
            for ach in achievements:
                writer.writerow([
                    ach.achievement_key,
                    ach.name,
                    ach.description,
                    ach.stat_key,
                    ach.category,
                    ach.tiers
                ])
                count += 1
            
            print(f"Successfully exported {count} achievements to {csv_path}.")
            
    except Exception as e:
        print(f"Error: {e}")
    finally:
        session.close()

if __name__ == "__main__":
    path = "data/achievements.csv"
    if len(sys.argv) > 1:
        path = sys.argv[1]
    export_achievements_to_csv(path)
