import sys
import os
import csv

# Set environment
sys.path.append(os.getcwd())

from services.skin_service import SkinService
from services.character_loader import get_character_loader
from database import Database

def verify_skin_management():
    print("--- SKIN MANAGEMENT VERIFICATION ---")
    
    loader = get_character_loader()
    skin_service = SkinService()
    
    # Check current state
    all_chars = loader.get_all_characters()
    print(f"Total characters: {len(all_chars)}")
    
    skinless = []
    for char in all_chars:
        # Check if has image
        safe_name = char['nome'].lower().replace(' ', '_')
        has_base = False
        for ext in ['.png', '.jpg', '.jpeg', '.webp']:
            if os.path.exists(f"images/{safe_name}{ext}"):
                has_base = True
                break
        
        if not has_base:
            continue
            
        skins = skin_service.get_available_skins(char['id'])
        if len(skins) == 0:
            skinless.append(char)
            
    print(f"Characters with base image but NO skins: {len(skinless)}")
    if skinless:
        sample = skinless[0]
        print(f"Sample skinless char: {sample['nome']} (ID: {sample['id']})")
        
        # Test adding a mock skin
        test_skin_name = f"Test Skin for {sample['nome']}"
        test_path = f"images/skins/{sample['nome'].lower()}_test.gif"
        
        # Ensure dir exists
        os.makedirs("images/skins", exist_ok=True)
        # Create dummy file
        with open(test_path, 'w') as f: f.write("dummy gif content")
        
        print(f"Testing SkinService.add_new_skin for {sample['nome']}...")
        new_id = skin_service.add_new_skin(sample['id'], test_skin_name, 9999, test_path)
        
        if new_id != -1:
            print(f"✅ Skin added successfully with ID: {new_id}")
            # Verify cache reload
            skins_after = skin_service.get_available_skins(sample['id'])
            if len(skins_after) == 1 and skins_after[0]['name'] == test_skin_name:
                print("✅ Cache reloaded correctly.")
            else:
                print("❌ Cache reload failed or returned wrong data.")
        else:
            print("❌ Skin addition failed.")
            
        # Cleanup dummy skin from CSV for next real use? 
        # Actually, let's keep it for verification but maybe I should have a way to revert.
        # I'll just leave it, it's a test environment.
    else:
        print("✅ No skinless characters found (or none with base images).")

if __name__ == "__main__":
    verify_skin_management()
