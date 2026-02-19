import csv
import sys
import os

# Add parent directory to path to import modules
sys.path.append(os.path.dirname(os.path.abspath(__file__)) + '/..')

from database import Database
from models.system import CharacterTransformation, Livello

def main():
    db = Database()
    session = db.get_session()
    
    try:
        # Load characters from CSV to find Saiyans
        saiyans = []
        with open('data/characters.csv', 'r') as f:
            reader = csv.DictReader(f)
            for row in reader:
                if row.get('subgroup') == 'Saiyan':
                    saiyans.append(row)
        
        print(f"Found {len(saiyans)} Saiyans.")
        
        # Great Ape ID
        GREAT_APE_ID = 500
        
        # Check if Great Ape exists in DB, if not user needs to sync characters
        # But for transformations table, we just need the IDs
        
        count = 0
        for saiyan in saiyans:
            base_id = int(saiyan['id'])
            
            # Skip if base_id is Great Ape itself
            if base_id == GREAT_APE_ID:
                continue
                
            # Check if transformation already exists
            existing = session.query(CharacterTransformation).filter_by(
                base_character_id=base_id,
                transformed_character_id=GREAT_APE_ID
            ).first()
            
            if not existing:
                trans = CharacterTransformation(
                    base_character_id=base_id,
                    transformed_character_id=GREAT_APE_ID,
                    transformation_name="Great Ape",
                    wumpa_cost=0, # Free as requested/implied for natural transformation
                    duration_days=0.5, # 12 hours (night) max
                    health_bonus=0, # Stats are handled by the character itself (base stats + bonus)
                    mana_bonus=0,
                    damage_bonus=0,
                    is_progressive=False,
                    required_level=1 # All Saiyans can do it
                )
                session.add(trans)
                count += 1
                
        session.commit()
        print(f"✅ Added {count} Great Ape transformations.")
        
    except Exception as e:
        print(f"Error: {e}")
        session.rollback()
    finally:
        session.close()

if __name__ == "__main__":
    main()
