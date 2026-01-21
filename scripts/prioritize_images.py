import csv
import os

def load_csv(filepath):
    with open(filepath, 'r') as f:
        reader = csv.DictReader(f)
        return list(reader)

def get_priority(item_type, name, characters, mobs, bosses):
    if item_type == 'character':
        for char in characters:
            if char['nome'] == name:
                return int(char['livello'])
        return 999 # Not found
    elif item_type == 'mob':
        for mob in mobs:
            if mob['nome'] == name:
                return int(mob['difficulty']) * 5 # Approx level
        return 999
    elif item_type == 'boss':
        for boss in bosses:
            if boss['nome'] == name:
                return 50 + (int(boss['loot_exp']) // 100) # High level
        return 999
    return 999

characters = load_csv('data/characters.csv')
mobs = load_csv('data/mobs.csv')
bosses = load_csv('data/bosses.csv')

missing_images = []
with open('missing_images_list.txt', 'r') as f:
    lines = f.readlines()
    if lines and "Found" in lines[0]:
        lines = lines[1:] # Skip header
    
    for line in lines:
        parts = line.strip().split('|')
        if len(parts) >= 3:
            item_type = parts[0]
            name = parts[1]
            path = parts[2]
            priority = get_priority(item_type, name, characters, mobs, bosses)
            missing_images.append({'type': item_type, 'name': name, 'path': path, 'priority': priority})

# Sort by priority
missing_images.sort(key=lambda x: x['priority'])

with open('prioritized_missing_images.txt', 'w') as f:
    for item in missing_images:
        f.write(f"{item['priority']}|{item['type']}|{item['name']}|{item['path']}\n")

print(f"Prioritized {len(missing_images)} images.")
