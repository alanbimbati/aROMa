"""
Seed achievements into database from achievements.json
"""

import json
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import Database
from models.achievements import Achievement

def seed_achievements():
    """Populate database with initial achievements"""
    db = Database()
    session = db.get_session()
    
    try:
        # Load achievements from JSON
        with open('data/achievements.json', 'r', encoding='utf-8') as f:
            achievements_data = json.load(f)
        
        added_count = 0
        updated_count = 0
        
        for ach_data in achievements_data:
            # Check if already exists
            existing = session.query(Achievement).filter(
                Achievement.achievement_key == ach_data['achievement_key']
            ).first()
            
            if existing:
                # Update existing achievement
                for key, value in ach_data.items():
                    setattr(existing, key, value)
                updated_count += 1
                print(f"  ✅ Updated: {ach_data['name']}")
            else:
                # Create new achievement
                achievement = Achievement(**ach_data)
                session.add(achievement)
                added_count += 1
                print(f"  ➕ Added: {ach_data['name']}")
        
        session.commit()
        
        print(f"\n{'='*60}")
        print(f"✅ Seeding completed!")
        print(f"  Added: {added_count} achievements")
        print(f"  Updated: {updated_count} achievements")
        print(f"  Total: {added_count + updated_count} achievements")
        
    except Exception as e:
        session.rollback()
        print(f"❌ Error seeding achievements: {e}")
        raise
    finally:
        session.close()

if __name__ == "__main__":
    print("🌱 Seeding achievements...\n")
    seed_achievements()
