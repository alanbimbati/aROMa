import csv
import os

def verify_images():
    entities_dir = 'images/'
    missing = []
    found = 0
    
    # Check Mobs
    print("Checking Mobs...")
    try:
        with open('data/mobs.csv', 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                name = row['nome']
                safe_name = name.lower().replace(" ", "_")
                exists = any(os.path.exists(f"{entities_dir}{safe_name}{ext}") for ext in ['.png', '.jpg', '.jpeg'])
                if exists:
                    found += 1
                else:
                    missing.append(f"Mob: {name}")
    except Exception as e:
        print(f"Error checking mobs: {e}")

    # Check Bosses
    print("Checking Bosses...")
    try:
        with open('data/bosses.csv', 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                name = row['nome']
                safe_name = name.lower().replace(" ", "_")
                exists = any(os.path.exists(f"{entities_dir}{safe_name}{ext}") for ext in ['.png', '.jpg', '.jpeg'])
                if exists:
                    found += 1
                else:
                    missing.append(f"Boss: {name}")
    except Exception as e:
        print(f"Error checking bosses: {e}")

    # Check Characters
    print("Checking Characters...")
    try:
        with open('data/characters.csv', 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                name = row['nome']
                safe_name = name.lower().replace(" ", "_")
                exists = any(os.path.exists(f"{entities_dir}{safe_name}{ext}") for ext in ['.png', '.jpg', '.jpeg'])
                if exists:
                    found += 1
                else:
                    missing.append(f"Character: {name}")
    except Exception as e:
        print(f"Error checking characters: {e}")

    print(f"\nVerification Complete!")
    print(f"Total found: {found}")
    print(f"Total missing: {len(missing)}")
    
    if missing:
        print("\nMissing Images:")
        for m in missing:
            print(f" - {m}")

if __name__ == "__main__":
    verify_images()
