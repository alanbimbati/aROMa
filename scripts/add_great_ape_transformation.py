#!/usr/bin/env python3
"""
Add Great Ape transformation for all Saiyan characters.
Creates database entries linking Saiyan characters to Great Ape (ID 500).
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import Database
from models.system import CharacterTransformation

# Saiyan character IDs that should be able to transform into Great Ape
SAIYAN_IDS = [
    60,   # Goku
    61,   # Vegeta  
    78,   # Goku SSJ
    79,   # Vegeta SSJ
    80,   # Gohan SSJ
    90,   # Goku SSJ2
    91,   # Vegeta SSJ2
    92,   # Gohan SSJ2
    108,  # Goku SSJ3
    109,  # Vegeta SSJ3
    120,  # Goku SSJ4
    121,  # Vegeta SSJ4
    144,  # Goku SSJ Blue
    145,  # Vegeta SSJ Blue
    150,  # Goku UI
    152,  # Broly
    281,  # Gohan Base
    284,  # Trunks Base
    285,  # Trunks SSJ
    286,  # Vegeta Ultra Ego
    291,  # Nappa
    292,  # Raditz
    301,  # Bardack
    302,  # Tarles
    303,  # Goku GT
    304,  # Vegeta GT
    305,  # Pan
    309,  # Goku SSJ4 (GT)
    310,  # Vegeta SSJ4 (GT)
    312,  # Bardack SSJ
]

GREAT_APE_ID = 500
WUMPA_COST = 0  # Set to 0 as requested/implied by user (they thought it was 3000 mana)
DURATION_DAYS = 0.5  # 12 hours
MANA_COST = 50  # User requested 50 mana cost

def main():
    db = Database()
    session = db.get_session()
    
    try:
        added = 0
        skipped = 0
        
        for saiyan_id in SAIYAN_IDS:
            # Check if transformation already exists
            existing = session.query(CharacterTransformation).filter_by(
                base_character_id=saiyan_id,
                transformed_character_id=GREAT_APE_ID
            ).first()
            
            if existing:
                # Update existing record if needed
                updated = False
                if getattr(existing, 'mana_cost', 0) != MANA_COST:
                    existing.mana_cost = MANA_COST
                    updated = True
                if existing.wumpa_cost != WUMPA_COST:
                    existing.wumpa_cost = WUMPA_COST
                    updated = True
                
                if updated:
                    print(f"Updated {saiyan_id} -> Great Ape: Mana={MANA_COST}, Wumpa={WUMPA_COST}")
                skipped += 1
                continue
            
            # Create new transformation
            transformation = CharacterTransformation(
                base_character_id=saiyan_id,
                transformed_character_id=GREAT_APE_ID,
                wumpa_cost=WUMPA_COST,
                mana_cost=MANA_COST,
                duration_days=DURATION_DAYS,
                is_time_restricted=True,  # Only at night (18:00-06:00)
                allowed_start_hour=18,
                allowed_end_hour=6,
                transformation_name="Scimmione"
            )
            
            session.add(transformation)
            added += 1
            print(f"Added {saiyan_id} -> Great Ape transformation")
        
        session.commit()
        print(f"\n✅ Done! Added: {added}, Skipped: {skipped}")
        
    except Exception as e:
        session.rollback()
        print(f"❌ Error: {e}")
        raise
    finally:
        session.close()

if __name__ == "__main__":
    main()
