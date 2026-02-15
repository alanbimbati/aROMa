#!/usr/bin/env python3
"""
Script to unify characters.csv, mobs.csv, and bosses.csv into a single characters.csv
with alignment and entity_type fields
"""
import csv
import os
import shutil
from datetime import datetime

# Paths
BASE_DIR = "/home/alan/Documenti/Coding/aroma"
DATA_DIR = os.path.join(BASE_DIR, "data")
BACKUP_DIR = os.path.join(BASE_DIR, f"backups/csv_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}")

def backup_files():
    """Backup original CSV files"""
    os.makedirs(BACKUP_DIR, exist_ok=True)
    for filename in ['characters.csv', 'mobs.csv', 'bosses.csv']:
        src = os.path.join(DATA_DIR, filename)
        dst = os.path.join(BACKUP_DIR, filename)
        shutil.copy2(src, dst)
        print(f"✅ Backed up {filename}")

def load_characters():
    """Load existing characters with Good/Neutral alignment"""
    characters = []
    with open(os.path.join(DATA_DIR, 'characters.csv'), 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            # Existing characters are playable
            row['entity_type'] = 'Playable'
            row['spawn_eligible'] = 'false'
            row['base_stat_multiplier'] = '1.0'
            
            # Assign alignment based on existing alignment or infer
            if 'alignment' not in row or not row['alignment']:
                row['alignment'] = 'Good'  # Default
            
            characters.append(row)
    
    print(f"📊 Loaded {len(characters)} characters")
    return characters

def load_mobs():
    """Convert mobs to Evil Mob entities"""
    mobs = []
    mob_id_start = 10000  # Start mob IDs from 10000
    
    with open(os.path.join(DATA_DIR, 'mobs.csv'), 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for idx, row in enumerate(reader, start=mob_id_start):
            # Convert mob to character format
            character = {
                'id': str(idx),
                'nome': row['nome'],
                'livello': '1',  # Mobs don't have fixed levels
                'lv_premium': '0',
                'exp_required': '0',
                'special_attack_name': row.get('attack_type', 'Strike'),
                'special_attack_damage': row['attack_damage'],
                'special_attack_mana_cost': '0',
                'price': '0',  # Cannot be purchased
                'description': row['description'],
                'character_group': row['series'],
                'max_concurrent_owners': '-1',
                'is_pokemon': '0',
                'elemental_type': 'Normal',
                'subgroup': row.get('saga', row['series']),
                'alignment': 'Evil',
                'crit_chance': '5',
                'crit_multiplier': '1.5',
                'required_character_id': '',
                'speed': row['speed'],
                'is_transformation': '0',
                'base_character_id': '',
                'transformation_mana_cost': '',
                'transformation_duration_days': '',
                'bonus_health': row['hp'],
                'bonus_mana': '50',
                'bonus_damage': '0',
                'bonus_resistance': '0',
                'bonus_crit': '0',
                'bonus_speed': '0',
                'special_attack_gif': '',
                'entity_type': 'Mob',
                'spawn_eligible': 'true',
                'base_stat_multiplier': '1.5',  # Mobs 50% stronger
            }
            mobs.append(character)
    
    print(f"👾 Converted {len(mobs)} mobs")
    return mobs

def load_bosses():
    """Convert bosses to Evil Boss entities"""
    bosses = []
    boss_id_start = 20000  # Start boss IDs from 20000
    
    with open(os.path.join(DATA_DIR, 'bosses.csv'), 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for idx, row in enumerate(reader, start=boss_id_start):
            # Convert boss to character format
            try:
                difficulty = int(row.get('difficulty', '5'))
            except (ValueError, KeyError):
                # If difficulty is not a number, default to 5
                difficulty = 5

            character = {
                'id': str(idx),
                'nome': row['nome'],
                'livello': str(difficulty * 10),  # Difficulty → Level
                'lv_premium': '0',
                'exp_required': '0',
                'special_attack_name': row.get('attack_type', 'Ultimate').title(),
                'special_attack_damage': row['attack_damage'],
                'special_attack_mana_cost': '100',
                'price': '0',  # Cannot be purchased
                'description': row['description'],
                'character_group': row['series'],
                'max_concurrent_owners': '1',  # Bosses are unique
                'is_pokemon': '0',
                'elemental_type': 'Normal',
                'subgroup': row.get('saga', row['series']),
                'alignment': 'Evil',
                'crit_chance': '15',
                'crit_multiplier': '2.0',
                'required_character_id': '',
                'speed': row['speed'],
                'is_transformation': '0',
                'base_character_id': '',
                'transformation_mana_cost': '',
                'transformation_duration_days': '',
                'bonus_health': row['hp'],
                'bonus_mana': '500',
                'bonus_damage': row['attack_damage'],
                'bonus_resistance': '50',
                'bonus_crit': '10',
                'bonus_speed': '0',
                'special_attack_gif': '',
                'entity_type': 'Boss',
                'spawn_eligible': 'true',  # Bosses can spawn in chat
                'base_stat_multiplier': '2.0',  # Bosses 100% stronger
            }
            bosses.append(character)
    
    print(f"👑 Converted {len(bosses)} bosses")
    return bosses

def write_unified_csv(characters, mobs, bosses):
    """Write unified characters.csv"""
    all_entities = characters + mobs + bosses
    
    # Define field order
    fieldnames = [
        'id', 'nome', 'livello', 'lv_premium', 'exp_required',
        'special_attack_name', 'special_attack_damage', 'special_attack_mana_cost',
        'price', 'description', 'character_group', 'max_concurrent_owners',
        'is_pokemon', 'elemental_type', 'subgroup', 'alignment',
        'crit_chance', 'crit_multiplier', 'required_character_id', 'speed',
        'is_transformation', 'base_character_id', 'transformation_mana_cost',
        'transformation_duration_days', 'bonus_health', 'bonus_mana',
        'bonus_damage', 'bonus_resistance', 'bonus_crit', 'bonus_speed',
        'special_attack_gif', 'entity_type', 'spawn_eligible', 'base_stat_multiplier'
    ]
    
    output_path = os.path.join(DATA_DIR, 'characters_unified.csv')
    with open(output_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(all_entities)
    
    print(f"✅ Written {len(all_entities)} entities to characters_unified.csv")
    return output_path

def main():
    print("🔄 Starting CSV unification...")
    print()
    
    # Backup
    print("📦 Creating backup...")
    backup_files()
    print()
    
    # Load data
    print("📖 Loading data...")
    characters = load_characters()
    mobs = load_mobs()
    bosses = load_bosses()
    print()
    
    # Write unified
    print("✍️  Writing unified CSV...")
    output_path = write_unified_csv(characters, mobs, bosses)
    print()
    
    print(f"✅ Unification complete!")
    print(f"📊 Total entities: {len(characters) + len(mobs) + len(bosses)}")
    print(f"   - Playable: {len(characters)}")
    print(f"   - Mobs: {len(mobs)}")
    print(f"   - Bosses: {len(bosses)}")
    print()
    print(f"📄 Output: {output_path}")
    print(f"💾 Backup: {BACKUP_DIR}")

if __name__ == "__main__":
    main()
