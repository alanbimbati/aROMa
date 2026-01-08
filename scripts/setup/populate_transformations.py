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
    
    for trans_data in transformations:
        transformation = CharacterTransformation(
            id=int(trans_data['id']),
            base_character_id=int(trans_data['base_character_id']) if trans_data['base_character_id'] else None,
            transformed_character_id=int(trans_data['transformed_character_id']) if trans_data['transformed_character_id'] else None,
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
