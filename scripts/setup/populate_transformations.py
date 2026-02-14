#!/usr/bin/env python3
"""
Populate transformation data from CSV
"""
import csv
from database import Database
from models.system import CharacterTransformation

def populate_transformations():
    db = Database()
    session = db.get_session()
    
    # Clear existing transformations
    session.query(CharacterTransformation).delete()
    
    # Read transformations CSV
    with open('data/transformations.csv', 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        transformations = list(reader)
    
    print(f"📋 Found {len(transformations)} transformations")
    
    from services.character_loader import get_character_loader
    char_loader = get_character_loader()
    
    for trans_data in transformations:
        # Find IDs by name
        base_char = char_loader.get_character_by_name(trans_data['base_character_name'])
        trans_char = char_loader.get_character_by_name(trans_data['transformed_character_name'])
        
        if not base_char or not trans_char:
            print(f"⚠️ Skipping '{trans_data['transformation_name']}': base or trans char not found!")
            continue
            
        transformation = CharacterTransformation(
            id=int(trans_data['id']),
            base_character_id=base_char['id'],
            transformed_character_id=trans_char['id'],
            transformation_name=trans_data['transformation_name'],
            wumpa_cost=int(trans_data['wumpa_cost']),
            duration_days=float(trans_data['duration_days']),
            health_bonus=int(trans_data['health_bonus']) if trans_data['health_bonus'] else 0,
            mana_bonus=int(trans_data['mana_bonus']) if trans_data['mana_bonus'] else 0,
            damage_bonus=int(trans_data['damage_bonus']) if trans_data['damage_bonus'] else 0,
            is_progressive=bool(int(trans_data['is_progressive'])) if trans_data['is_progressive'] else False,
            previous_transformation_id=int(trans_data['previous_transformation_id']) if trans_data['previous_transformation_id'] else None,
            required_level=int(trans_data['required_level']) if trans_data['required_level'] else None
        )
        session.add(transformation)
    
    session.commit()
    print(f"✅ Populated {len(transformations)} transformations")
    
    # Show examples
    print("\n📊 Example transformations:")
    examples = session.query(CharacterTransformation).limit(5).all()
    for trans in examples:
        print(f"  - {trans.transformation_name}: +{trans.health_bonus} HP, +{trans.damage_bonus} DMG, {trans.wumpa_cost} Wumpa")
    
    session.close()

if __name__ == "__main__":
    populate_transformations()
