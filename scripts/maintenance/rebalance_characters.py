#!/usr/bin/env python3
"""
Rebalance all characters with stat bonuses
"""
import csv

INPUT_FILE = "data/characters.csv"
OUTPUT_FILE = "data/characters_rebalanced.csv"

def calculate_bonuses(level, is_premium):
    """Calculate balanced stat bonuses based on level"""
    # Base formula: scale with level
    bonus_health = level * 15  # 15 HP per level
    bonus_mana = level * 8     # 8 mana per level
    bonus_damage = level * 2   # 2 damage per level
    bonus_resistance = min(level // 5, 15)  # Max 15%, cap at lv75
    bonus_crit = min(level // 3, 20)  # Max 20%, cap at lv60
    bonus_speed = level * 3    # 3 speed per level
    
    # Premium characters get 20% bonus
    if is_premium:
        bonus_health = int(bonus_health * 1.2)
        bonus_mana = int(bonus_mana * 1.2)
        bonus_damage = int(bonus_damage * 1.2)
    
    return {
        'bonus_health': bonus_health,
        'bonus_mana': bonus_mana,
        'bonus_damage': bonus_damage,
        'bonus_resistance': bonus_resistance,
        'bonus_crit': bonus_crit,
        'bonus_speed': bonus_speed
    }

def main():
    print("Reading characters.csv...")
    
    with open(INPUT_FILE, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames
        rows = list(reader)
    
    # Add new columns
    new_fields = ['bonus_health', 'bonus_mana', 'bonus_damage', 'bonus_resistance', 'bonus_crit', 'bonus_speed']
    fieldnames = list(fieldnames) + new_fields
    
    print(f"Processing {len(rows)} characters...")
    
    # Process each character
    for row in rows:
        level = int(row['livello'])
        is_premium = int(row.get('lv_premium', 0)) == 1
        
        bonuses = calculate_bonuses(level, is_premium)
        
        # Add bonuses to row
        for key, value in bonuses.items():
            row[key] = value
    
    # Special equalization: Shulk = Squall level
    for row in rows:
        if row['nome'] == 'Shulk':
            print(f"Equalizing Shulk (was Lv{row['livello']}) to Squall...")
            row['livello'] = '11'  # Same as Squall
            row['exp_required'] = '5525'  # Same as Squall
            # Recalculate bonuses
            bonuses = calculate_bonuses(11, True)  # Premium
            for key, value in bonuses.items():
                row[key] = value
            # Adjust damage to be similar
            row['special_attack_damage'] = '110'  # Same as Squall
            row['special_attack_mana_cost'] = '52'
            print(f"  New Shulk: Lv11, 110 dmg")
    
    # Write output
    print(f"Writing to {OUTPUT_FILE}...")
    with open(OUTPUT_FILE, 'w', encoding='utf-8', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    
    print("✅ Done! Review the file and replace characters.csv if satisfied.")
    print(f"\nTo apply: mv {OUTPUT_FILE} {INPUT_FILE}")

if __name__ == "__main__":
    main()
