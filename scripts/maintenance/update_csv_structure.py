"""
Script to update characters.csv with new columns
"""
import csv
import shutil
import os

INPUT_FILE = "data/characters.csv"
BACKUP_FILE = "data/characters_backup.csv"
TEMP_FILE = "data/characters_temp.csv"

NEW_COLUMNS = {
    "elemental_type": "Normal",
    "crit_chance": "5",
    "crit_multiplier": "1.5",
    "required_character_id": ""
}

def update_csv():
    if not os.path.exists(INPUT_FILE):
        print("Input file not found.")
        return

    # Backup
    shutil.copy(INPUT_FILE, BACKUP_FILE)
    print(f"Backup created at {BACKUP_FILE}")

    with open(INPUT_FILE, 'r', encoding='utf-8') as infile, \
         open(TEMP_FILE, 'w', encoding='utf-8', newline='') as outfile:
        
        reader = csv.DictReader(infile)
        fieldnames = reader.fieldnames + list(NEW_COLUMNS.keys())
        
        writer = csv.DictWriter(outfile, fieldnames=fieldnames)
        writer.writeheader()
        
        for row in reader:
            for col, default_val in NEW_COLUMNS.items():
                row[col] = default_val
            writer.writerow(row)
            
    shutil.move(TEMP_FILE, INPUT_FILE)
    print("CSV updated successfully.")

if __name__ == "__main__":
    update_csv()
