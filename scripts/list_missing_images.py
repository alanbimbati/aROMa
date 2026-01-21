import os
import sys

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.character_service import CharacterService
from services.pve_service import PvEService

character_service = CharacterService()
pve_service = PvEService()

missing_images = []

# 1. Check Characters
all_chars = character_service.get_all_characters()
for char in all_chars:
    image_exists = False
    char_name_lower = char['nome'].lower().replace(" ", "_")
    for ext in ['.png', '.jpg', '.jpeg']:
        if os.path.exists(f"images/characters/{char_name_lower}{ext}"):
            image_exists = True
            break
    
    if not image_exists:
        # Check base name
        base_name = char['nome'].split('-')[0].strip().lower().replace(" ", "_")
        for ext in ['.png', '.jpg', '.jpeg']:
            if os.path.exists(f"images/characters/{base_name}{ext}"):
                image_exists = True
                break
    
    if not image_exists:
        missing_images.append({'type': 'character', 'name': char['nome'], 'path': f"images/characters/{char_name_lower}.png"})

# 2. Check Mobs
if pve_service.mob_data:
    for mob in pve_service.mob_data:
        mob_name_lower = mob['nome'].lower().replace(" ", "_")
        image_exists = False
        for ext in ['.png', '.jpg', '.jpeg']:
            if os.path.exists(f"images/mobs/{mob_name_lower}{ext}"):
                image_exists = True
                break
        
        if not image_exists:
            missing_images.append({'type': 'mob', 'name': mob['nome'], 'path': f"images/mobs/{mob_name_lower}.png"})

# 3. Check Bosses
if pve_service.boss_data:
    for boss in pve_service.boss_data:
        boss_name_lower = boss['nome'].lower().replace(" ", "_")
        image_exists = False
        for ext in ['.png', '.jpg', '.jpeg']:
            if os.path.exists(f"images/bosses/{boss_name_lower}{ext}"):
                image_exists = True
                break
        
        if not image_exists:
            missing_images.append({'type': 'boss', 'name': boss['nome'], 'path': f"images/bosses/{boss_name_lower}.png"})

print(f"Found {len(missing_images)} missing images:")
for item in missing_images:
    print(f"{item['type']}|{item['name']}|{item['path']}")
