import csv
import math

INPUT_FILE = 'data/characters.csv'
OUTPUT_FILE = 'data/characters_rebalanced.csv'

# Role Definitions
ROLE_TANK = 'tank' # High HP, Res
ROLE_DPS = 'dps'   # High Dmg, Crit
ROLE_MAGE = 'mage' # High Mana, Dmg
ROLE_SPEED = 'speed' # High Speed, Dmg
ROLE_BALANCED = 'balanced' # Mix

# Heuristics for Role Assignment
TANK_KEYWORDS = ['Bowser', 'Hulk', 'Shield', 'Golem', 'Knight', 'Wall', 'Armored', 'Big', 'Tank', 'Heavy', 'Freezer', 'Cell']
MAGE_KEYWORDS = ['Zelda', 'Mage', 'Witch', 'Wizard', 'Psionic', 'Magic', 'Strange', 'Vivi', 'Yuna', 'Aerith', 'Palutena', 'Rosalina', 'Mewtwo']
SPEED_KEYWORDS = ['Sonic', 'Shadow', 'Flash', 'Quick', 'Ninja', 'Speed', 'Tracer', 'Scout', 'Fox', 'Falco', 'Gohan']
DPS_KEYWORDS = ['Goku', 'Vegeta', 'Sora', 'Cloud', 'Sephiroth', 'Link', 'Dante', 'Kratos', 'Doom', 'Samus', 'Zero']

def get_role(name, group):
    name_lower = name.lower()
    
    # Specific overrides
    if 'doom' in name_lower: return ROLE_TANK # Doom Slayer is tough
    if 'gohan' in name_lower: return ROLE_SPEED # User request
    if 'goku' in name_lower: return ROLE_MAGE # Needs lots of mana for Kamehameha, strictly speaking DPS/Mage hybrid but lets ensure mana
    
    for kw in TANK_KEYWORDS:
        if kw.lower() in name_lower: return ROLE_TANK
    for kw in MAGE_KEYWORDS:
        if kw.lower() in name_lower: return ROLE_MAGE
    for kw in SPEED_KEYWORDS:
        if kw.lower() in name_lower: return ROLE_SPEED
        
    return ROLE_BALANCED # Default fallback, handles most DPS well enough or we tune Balanced to be slightly DPS-leaning

def calculate_bonuses(role, level, special_cost):
    # Base Stats (Same for everyone)
    # HP: 100, Mana: 50, Dmg: 10
    
    bonuses = {
        'bonus_health': 0,
        'bonus_mana': 0,
        'bonus_damage': 0,
        'bonus_resistance': 0,
        'bonus_crit': 0,
        'bonus_speed': 0
    }
    
    # Multipliers per Level
    hp_mult = 5
    mana_mult = 2
    dmg_mult = 1
    
    if role == ROLE_TANK:
        hp_mult = 10 # Lv 40 -> +400 HP
        bonuses['bonus_resistance'] = min(25, int(level * 0.5)) # Cap 25% res from char
        dmg_mult = 0.8
    elif role == ROLE_MAGE:
        hp_mult = 4
        mana_mult = 5 # Lots of mana
        dmg_mult = 1.2
    elif role == ROLE_SPEED:
        hp_mult = 5
        bonuses['bonus_speed'] = int(level * 0.5)
        dmg_mult = 1.1
    elif role == ROLE_BALANCED:
        hp_mult = 6
        dmg_mult = 1.0
        
    # Calculate Raw Bonuses
    bonuses['bonus_health'] = int(level * hp_mult)
    bonuses['bonus_mana'] = int(level * mana_mult)
    bonuses['bonus_damage'] = int(level * dmg_mult)
    
    # Mana Fix: Ensure at least 2x Special Attacks
    # Total Mana = 50 + Alloc + Bonus. We ignore Alloc for minimum guarantee.
    # Needed = Cost * 2.
    # Bonus >= (Cost * 2) - 50.
    needed_mana = (special_cost * 2) - 50
    if bonuses['bonus_mana'] < needed_mana:
        bonuses['bonus_mana'] = max(bonuses['bonus_mana'], needed_mana)
        # Ensure it's not negative if cost is low
        if bonuses['bonus_mana'] < 0: bonuses['bonus_mana'] = 0

    return bonuses

def process_csv():
    with open(INPUT_FILE, 'r', encoding='utf-8') as f_in, \
         open(OUTPUT_FILE, 'w', encoding='utf-8', newline='') as f_out:
        
        reader = csv.DictReader(f_in)
        fieldnames = reader.fieldnames
        
        # Ensure bonus columns exist
        bonus_cols = ['bonus_health', 'bonus_mana', 'bonus_damage', 'bonus_resistance', 'bonus_crit', 'bonus_speed']
        for col in bonus_cols:
            if col not in fieldnames:
                fieldnames.append(col)
        
        writer = csv.DictWriter(f_out, fieldnames=fieldnames)
        writer.writeheader()
        
        for row in reader:
            name = row['nome']
            group = row['character_group']
            level = int(row['livello'])
            special_cost = int(row.get('special_attack_mana_cost', 0) or 0)
            
            role = get_role(name, group)
            bonuses = calculate_bonuses(role, level, special_cost)
            
            # Update row
            for k, v in bonuses.items():
                row[k] = v
                
            writer.writerow(row)
            print(f"Update {name} (Lv {level}, {role}): HP+{bonuses['bonus_health']}, Mana+{bonuses['bonus_mana']}")

if __name__ == "__main__":
    process_csv()
