#!/usr/bin/env python3
"""
Seed Crafting and Equipment Data
Populate resources and equipment tables from CSV and hardcoded values.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from database import Database
from sqlalchemy import text
import csv
import json

def seed_resources():
    """Populate resources table"""
    db = Database()
    session = db.get_session()
    
    print("📦 Seeding resources...")
    
    resources = [
        # Common (Rarity 1)
        {'name': 'Rottami', 'rarity': 1, 'description': 'Rusty metal fragments (Iron Scrap)', 'drop_source': 'mob'},
        {'name': 'Cuoio', 'rarity': 1, 'description': 'Tattered leather pieces (Worn Leather)', 'drop_source': 'mob'},
        {'name': 'Legna', 'rarity': 1, 'description': 'Rough wooden board (Wood Plank)', 'drop_source': 'both'},
        {'name': 'Cristallo Verde', 'rarity': 1, 'description': 'A glowing green crystal', 'drop_source': 'both'},
        
        # Uncommon (Rarity 2)
        {'name': 'Ferro', 'rarity': 2, 'description': 'A solid steel ingot (Steel Bar)', 'drop_source': 'mob'},
        {'name': 'Pelle Dura', 'rarity': 2, 'description': 'Durable leather hide (Tough Leather)', 'drop_source': 'mob'},
        {'name': 'Cristallo Blu', 'rarity': 2, 'description': 'A pulsing blue crystal', 'drop_source': 'both'},
        {'name': 'Scaglia di Drago', 'rarity': 2, 'description': 'Fragment of dragon scale', 'drop_source': 'mob'},
        
        # Rare (Rarity 3)
        {'name': 'Mithril', 'rarity': 3, 'description': 'Lightweight rare metal', 'drop_source': 'mob'},
        {'name': 'Cristallo Rosso', 'rarity': 3, 'description': 'A fiery red crystal', 'drop_source': 'both'},
        {'name': 'Frammento Stellare', 'rarity': 3, 'description': 'A piece of fallen star', 'drop_source': 'mob'},
        {'name': 'Essenza Energetica', 'rarity': 3, 'description': 'Condensed pure energy', 'drop_source': 'both'},
        {'name': 'Seta', 'rarity': 3, 'description': 'Fine silk cloth', 'drop_source': 'mob'},
        {'name': 'Essenza Elementale', 'rarity': 3, 'description': 'Elemental essence', 'drop_source': 'mob'},
        
        # Epic (Rarity 4)
        {'name': 'Adamantite', 'rarity': 4, 'description': 'Nearly indestructible metal', 'drop_source': 'mob'},
        {'name': 'Cristallo Viola', 'rarity': 4, 'description': 'A mysterious purple crystal', 'drop_source': 'both'},
        {'name': 'Frammento Antico', 'rarity': 4, 'description': 'Relic from ancient times', 'drop_source': 'mob'},
        {'name': 'Essenza del Caos', 'rarity': 4, 'description': 'Volatile chaotic energy', 'drop_source': 'both'},
        
        # Legendary (Rarity 5)
        {'name': 'Oricalco', 'rarity': 5, 'description': 'The legendary divine metal', 'drop_source': 'mob'},
        {'name': 'Cristallo Dorato', 'rarity': 5, 'description': 'A radiant golden crystal', 'drop_source': 'both'},
        {'name': 'Frammento Divino', 'rarity': 5, 'description': 'Fragment of godly power', 'drop_source': 'mob'},
        {'name': 'Essenza Eterna', 'rarity': 5, 'description': 'Essence that never fades', 'drop_source': 'both'},
        {'name': 'Nucleo Stellare', 'rarity': 5, 'description': 'Core of a star', 'drop_source': 'mob'},
    ]
    
    # Note: I renamed some english names to Italian to match the CSV requirements (Rotttami, Ferro, Cuoio...)
    
    count = 0
    try:
        for res in resources:
            exists = session.execute(
                text("SELECT id FROM resources WHERE name = :name"),
                {"name": res['name']}
            ).fetchone()
            
            if not exists:
                session.execute(text("""
                    INSERT INTO resources (name, rarity, description, drop_source)
                    VALUES (:name, :rarity, :description, :drop_source)
                """), res)
                count += 1
        session.commit()
        print(f"✅ Added {count} new resources.")
    except Exception as e:
        print(f"❌ Error seeding resources: {e}")
        session.rollback()
    finally:
        session.close()

def seed_equipment():
    """Populate equipment table from CSV"""
    db = Database()
    session = db.get_session()
    
    print("⚔️  Seeding equipment...")
    
    try:
        with open('data/equipment.csv', 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            count = 0
            
            for row in reader:
                try:
                    eq_id = int(row['id'])
                    
                    # Prepare data
                    data = {
                        'id': eq_id,
                        'name': row['name'],
                        'slot': row['slot'],
                        'rarity': int(row['rarity']),
                        'min_level': int(row['min_level']),
                        'stats_json': row['stats_json'], # Keep as string/json
                        'crafting_time': int(row['crafting_time']) if row['crafting_time'] else 0,
                        'crafting_requirements': row['crafting_requirements'],
                        'description': row['description'],
                        'set_name': row.get('set_name'),
                        'effect_type': row.get('effect_type') # Optional
                    }
                    
                    # Check existence
                    exists = session.execute(text("SELECT id FROM equipment WHERE id = :id"), {'id': eq_id}).fetchone()
                    
                    if exists:
                        # Update
                        session.execute(text("""
                            UPDATE equipment 
                            SET name=:name, slot=:slot, rarity=:rarity, min_level=:min_level, 
                                stats_json=:stats_json, crafting_time=:crafting_time, 
                                crafting_requirements=:crafting_requirements, description=:description,
                                set_name=:set_name, effect_type=:effect_type
                            WHERE id=:id
                        """), data)
                    else:
                        # Insert
                        session.execute(text("""
                            INSERT INTO equipment (id, name, slot, rarity, min_level, stats_json, 
                                                  crafting_time, crafting_requirements, description, set_name, effect_type)
                            VALUES (:id, :name, :slot, :rarity, :min_level, :stats_json, 
                                   :crafting_time, :crafting_requirements, :description, :set_name, :effect_type)
                        """), data)
                        
                    count += 1
                except Exception as e:
                    print(f"⚠️  Error processing equipment {row.get('name', '?')}: {e}")
            
            session.commit()
            print(f"✅ Processed {count} equipment items.")
            
    except Exception as e:
        print(f"❌ Error seeding equipment: {e}")
        session.rollback()
    finally:
        session.close()

if __name__ == "__main__":
    seed_resources()
    seed_equipment()
