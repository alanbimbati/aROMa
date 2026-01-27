from database import Database
from models.achievements import Achievement
import sys

def check_level_ach():
    print("Searching for level-related achievements...")
    db = Database()
    session = db.get_session()
    
    try:
        achs = session.query(Achievement).filter(
            (Achievement.name.ilike('%livello%')) | 
            (Achievement.achievement_key.ilike('%level%'))
        ).all()
        
        if not achs:
            print("No achievements found.")
        
        for ach in achs:
            print(f"Key: {ach.achievement_key}")
            print(f"Name: {ach.name}")
            print(f"Description: {ach.description}")
            print(f"Tiers: {ach.tiers}")
            print("-" * 20)
            
    except Exception as e:
        print(f"Error: {e}")
    finally:
        session.close()

if __name__ == "__main__":
    check_level_ach()
