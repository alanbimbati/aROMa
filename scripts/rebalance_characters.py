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
MAGE_KEYWORDS = ['Zelda', 'Mage', 'Witch', 'Wizard', 'Psionic', 'Magic', 'Strange', 'Vivi', 'Yuna', 'Aerith', 'Palutena', 'Rosalina', 'Mewtwo', 'Goku'] # Goku needs mana!
SPEED_KEYWORDS = ['Sonic', 'Shadow', 'Flash', 'Quick', 'Ninja', 'Speed', 'Tracer', 'Scout', 'Fox', 'Falco', 'Gohan']
DPS_KEYWORDS = ['Vegeta', 'Sora', 'Cloud', 'Sephiroth', 'Link', 'Dante', 'Kratos', 'Doom', 'Samus', 'Zero']

# Stat Conversion Rates (1 Point = X Stat)
CONVERSION = {
    'health': 10,
    'mana': 5,
    'damage': 2,
    'resistance': 1, # Max 75%
    'crit': 1,
    'speed': 1 
}

def get_role(name, group):
    name_lower = name.lower()
    
    # Specific overrides
    if 'doom' in name_lower: return ROLE_TANK # Doom Slayer: Tanky DPS
    if 'gohan' in name_lower: return ROLE_SPEED 
    
    for kw in TANK_KEYWORDS:
        if kw.lower() in name_lower: return ROLE_TANK
    for kw in MAGE_KEYWORDS:
        if kw.lower() in name_lower: return ROLE_MAGE
    for kw in SPEED_KEYWORDS:
        if kw.lower() in name_lower: return ROLE_SPEED
    for kw in DPS_KEYWORDS:
        if kw.lower() in name_lower: return ROLE_DPS
        
    return ROLE_BALANCED

def calculate_distribution(role, total_points):
    # Distribution Weights (Must sum to 1.0)
    weights = {
        'health': 0.0,
        'mana': 0.0,
        'damage': 0.0,
        'resistance': 0.0,
        'crit': 0.0,
        'speed': 0.0
    }
    
    if role == ROLE_TANK:
        weights = {'health': 0.5, 'mana': 0.0, 'damage': 0.2, 'resistance': 0.2, 'crit': 0.0, 'speed': 0.1}
    elif role == ROLE_MAGE:
        weights = {'health': 0.2, 'mana': 0.4, 'damage': 0.3, 'resistance': 0.0, 'crit': 0.1, 'speed': 0.0}
    elif role == ROLE_DPS:
        weights = {'health': 0.2, 'mana': 0.1, 'damage': 0.4, 'resistance': 0.0, 'crit': 0.1, 'speed': 0.2}
    elif role == ROLE_SPEED:
        weights = {'health': 0.2, 'mana': 0.1, 'damage': 0.2, 'resistance': 0.0, 'crit': 0.1, 'speed': 0.4}
    else: # Balanced
        weights = {'health': 0.3, 'mana': 0.1, 'damage': 0.3, 'resistance': 0.1, 'crit': 0.1, 'speed': 0.1}
        
    # Distribute Points
    points = {}
    remaining = total_points
    
    # Pass 1: Assign integer points based on weights
    for stat, weight in weights.items():
        p = int(total_points * weight)
        points[stat] = p
        remaining -= p
        
    # Pass 2: Distribute remaining points to highest weight stat
    if remaining > 0:
        # Sort by weight desc
        sorted_stats = sorted(weights.items(), key=lambda x: x[1], reverse=True)
        for stat, _ in sorted_stats:
            if remaining <= 0: break
            points[stat] += 1
            remaining -= 1
            
    return points

def calculate_bonuses(role, level):
    total_points = level # 1 Point per Level
    
    # Limit Total Points if level > 100 to avoid craziness? No, user wants linear scaling.
    
    points_dist = calculate_distribution(role, total_points)
    
    bonuses = {
        'bonus_health': points_dist['health'] * CONVERSION['health'],
        'bonus_mana': points_dist['mana'] * CONVERSION['mana'],
        'bonus_damage': points_dist['damage'] * CONVERSION['damage'],
        'bonus_resistance': points_dist['resistance'] * CONVERSION['resistance'],
        'bonus_crit': points_dist['crit'] * CONVERSION['crit'],
        'bonus_speed': points_dist['speed'] * CONVERSION['speed']
    }
    
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
            
            role = get_role(name, group)
            bonuses = calculate_bonuses(role, level)
            
            # Update row
            for k, v in bonuses.items():
                row[k] = v
                
            writer.writerow(row)
            if 'Doom' in name or 'Goku' in name:
                print(f"Update {name} (Lv {level}, {role}): {bonuses}")

if __name__ == "__main__":
    process_csv()
