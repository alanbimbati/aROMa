#!/usr/bin/env python3
import csv
import os
import sys

# Define target paths
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CSV_PATH = os.path.join(BASE_DIR, 'data', 'characters.csv')

def get_saiyans(csv_path):
    saiyans = []
    with open(csv_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row.get('subgroup') == 'Saiyan' and row.get('nome') != 'Great Ape' and row.get('is_transformation') == '0':
                saiyans.append(row)
    return saiyans

def get_generic_great_ape(csv_path):
    with open(csv_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row.get('id') == '500':
                return row
    return None

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

def get_character_map(csv_path):
    cmap = {}
    with open(csv_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            cmap[int(row['id'])] = row
    return cmap

def main():
    cmap = get_character_map(CSV_PATH)
    generic_ape = cmap.get(500)
    
    if not generic_ape:
        print("Error: Generic Great Ape (ID 500) not found!")
        return

    new_apes = []
    start_id = 600
    
    for i, (identity, saiyan_ids) in enumerate(IDENTITY_MAPPING.items()):
        new_id = start_id + i
        ape_name = f"Scimmione ({identity})"
        
        # Determine level: max(30, max_level_of_variants)
        max_variant_lv = 0
        for s_id in saiyan_ids:
            variant = cmap.get(s_id)
            if variant:
                max_variant_lv = max(max_variant_lv, int(variant.get('livello', 1)))
        
        final_level = max(30, max_variant_lv)
        
        # Scaling factor: if level > 30, scale stats
        scale = 1.0
        if final_level > 30:
            scale = final_level / 30.0
            
        # Create consolidated Great Ape
        new_ape = generic_ape.copy()
        new_ape['id'] = str(new_id)
        new_ape['nome'] = ape_name
        new_ape['livello'] = str(final_level)
        new_ape['base_character_id'] = str(saiyan_ids[0]) # Use first variant as base for metadata
        new_ape['description'] = f"La trasformazione in Oozaru di {identity}"
        
        # Base stats around level 30 were: HP 150, Res 15
        new_ape['bonus_health'] = str(int(150 * scale))
        new_ape['bonus_resistance'] = str(int(15 * scale))
        new_ape['transformation_mana_cost'] = "50"
        new_ape['price'] = "3000"
        new_ape['is_transformation'] = "1"
        
        # Add to list
        new_apes.append(new_ape)
        print(f"Prepared: {ape_name} (ID: {new_id}, Level: {final_level}, Scale: {scale:.2f})")

    # Read existing characters
    with open(CSV_PATH, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames
        rows = list(reader)

    # Remove any existing unique apes (600-699) AND the generic one (500)
    rows = [r for r in rows if not (600 <= int(r['id']) < 700) and r['id'] != '500']
    
    # Add new ones
    rows.extend(new_apes)
    
    # Sort by ID
    rows.sort(key=lambda x: int(x['id']))

    # Write back to CSV
    with open(CSV_PATH, 'w', encoding='utf-8', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    
    print(f"\n✅ CSV Updated with {len(new_apes)} unique Great Ape forms.")

if __name__ == "__main__":
    main()
