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
        
        # Create consolidated Great Ape
        new_ape = generic_ape.copy()
        new_ape['id'] = str(new_id)
        new_ape['nome'] = ape_name
        new_ape['livello'] = "30"  # All Apes are level 30
        new_ape['base_character_id'] = str(saiyan_ids[0]) # Use first variant as base for metadata
        new_ape['description'] = f"La trasformazione in Oozaru di {identity}"
        new_ape['bonus_health'] = "150"
        new_ape['bonus_resistance'] = "15"
        new_ape['transformation_mana_cost'] = "50"
        new_ape['price'] = "3000"
        new_ape['is_transformation'] = "1"
        
        # Add to list
        new_apes.append(new_ape)
        print(f"Prepared: {ape_name} (ID: {new_id}) for Identity: {identity}")

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
