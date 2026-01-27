import os
import sys

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.character_service import CharacterService
from services.pve_service import PvEService

character_service = CharacterService()
pve_service = PvEService()

def check_image_exists(name):
    safe_name = name.lower().replace(" ", "_")
    # Check root entities dir
    for ext in ['.png', '.jpg', '.jpeg']:
        if os.path.exists(f"images/miscellania/{safe_name}{ext}"):
            return True
    return False

missing_images = []

# 1. Check Characters
all_chars = character_service.get_all_characters()
for char in all_chars:
    if not check_image_exists(char['nome']):
        # Check base name
        base_name = char['nome'].split('-')[0].strip()
        if not check_image_exists(base_name):
            missing_images.append({'type': 'character', 'name': char['nome'], 'path': f"images/miscellania/{char['nome'].lower().replace(' ', '_')}.png"})

# 2. Check Mobs
if pve_service.mob_data:
    for mob in pve_service.mob_data:
        if not check_image_exists(mob['nome']):
            missing_images.append({'type': 'mob', 'name': mob['nome'], 'path': f"images/miscellania/{mob['nome'].lower().replace(' ', '_')}.png"})

# 3. Check Bosses
if pve_service.boss_data:
    for boss in pve_service.boss_data:
        if not check_image_exists(boss['nome']):
            missing_images.append({'type': 'boss', 'name': boss['nome'], 'path': f"images/miscellania/{boss['nome'].lower().replace(' ', '_')}.png"})

print(f"Found {len(missing_images)} missing images:")
with open('missing_images_list.txt', 'w') as f:
    f.write(f"Found {len(missing_images)} missing images:\n")
    for item in missing_images:
        line = f"{item['type']}|{item['name']}|{item['path']}"
        print(line)
        f.write(line + "\n")
