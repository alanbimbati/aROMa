import os
import sys
sys.path.append(os.getcwd())

from services.dungeon_service import DungeonService

def check_dungeons():
    print("Checking DungeonService...")
    ds = DungeonService()
    print(f"Dungeons Cache Keys: {list(ds.dungeons_cache.keys())}")
    print(f"Dungeons Cache Content: {ds.dungeons_cache}")
    
    if not ds.dungeons_cache:
        print("ERROR: Dungeons cache is empty!")
        # Try to read file directly to debug
        try:
            with open('data/dungeons.csv', 'r') as f:
                print("dungeons.csv content:")
                print(f.read())
        except Exception as e:
            print(f"Error reading dungeons.csv: {e}")
    else:
        print("SUCCESS: Dungeons loaded.")

if __name__ == "__main__":
    check_dungeons()
