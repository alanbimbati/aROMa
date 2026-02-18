#!/usr/bin/env python3
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import Database
from models.system import CharacterTransformation

# Identity mapping for Saiyans
IDENTITY_MAPPING = {
    "Goku": [60, 78, 90, 108, 120, 144, 150, 303, 309],
    "Vegeta": [61, 79, 91, 109, 121, 145, 286, 304, 310],
    "Gohan": [80, 92, 281],
    "Trunks": [284, 285],
    "Nappa": [291],
    "Raditz": [292],
    "Bardack": [301, 312],
    "Tarles": [302],
    "Broly": [152],
    "Pan": [305],
    "Gogeta": [311]
}

WUMPA_COST = 3000
MANA_COST = 150
DURATION_DAYS = 0.5  # 12 hours

def main():
    db = Database()
    session = db.get_session()
    
    try:
        updated = 0
        added = 0
        deleted = 0
        
        # 1. Clean up old mappings
        # Delete generic (500) and any unique non-consolidated ones (600-699)
        # to ensure a fresh state for consolidation.
        all_saiyan_ids = [id for ids in IDENTITY_MAPPING.values() for id in ids]
        
        session.query(CharacterTransformation).filter(
            CharacterTransformation.base_character_id.in_(all_saiyan_ids),
            (CharacterTransformation.transformed_character_id == 500) | 
            ((CharacterTransformation.transformed_character_id >= 600) & (CharacterTransformation.transformed_character_id < 700))
        ).delete(synchronize_session=False)
        session.commit() # Commit delete first
        
        # 2. Add consolidated mappings
        for i, (identity, saiyan_ids) in enumerate(IDENTITY_MAPPING.items()):
            unique_ape_id = 600 + i
            
            for saiyan_id in saiyan_ids:
                # Create transformation record
                transformation = CharacterTransformation(
                    base_character_id=saiyan_id,
                    transformed_character_id=unique_ape_id,
                    wumpa_cost=WUMPA_COST,
                    mana_cost=MANA_COST,
                    duration_days=DURATION_DAYS,
                    is_time_restricted=True,
                    allowed_start_hour=18,
                    allowed_end_hour=6,
                    transformation_name="Scimmione"
                )
                session.add(transformation)
                added += 1
                
            print(f"Mapped Identity '{identity}' variants -> {unique_ape_id}")
            
        session.commit()
        print(f"\n✅ Done! Added: {added} mappings for {len(IDENTITY_MAPPING)} identities.")
        
    except Exception as e:
        session.rollback()
        print(f"❌ Error: {e}")
        raise
    finally:
        session.close()

if __name__ == "__main__":
    main()
