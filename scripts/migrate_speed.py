import csv
import sqlite3
import os

def migrate_csvs():
    print("Migrating CSVs...")
    
    # Characters
    try:
        rows = []
        with open('data/characters.csv', 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            fieldnames = reader.fieldnames
            if 'speed' not in fieldnames:
                fieldnames.append('speed')
            
            for row in reader:
                if 'speed' not in row or not row['speed']:
                    # Default speed based on level/group logic could go here
                    # For now, base speed 50 + level
                    lvl = int(row.get('livello', 1))
                    row['speed'] = 50 + lvl
                    
                    # Group specific adjustments
                    name = row.get('nome', '')
                    group = row.get('character_group', '')
                    if 'Sonic' in group or 'Flash' in name:
                        row['speed'] = int(row['speed']) + 30
                    elif 'Mario' in group:
                        row['speed'] = int(row['speed']) + 10
                    elif 'Bowser' in name or 'Ganondorf' in name:
                        row['speed'] = int(row['speed']) - 10 # Slower but stronger
                
                rows.append(row)
        
        with open('data/characters.csv', 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)
        print("Updated characters.csv")
            
    except Exception as e:
        print(f"Error updating characters.csv: {e}")

    # Mobs
    try:
        rows = []
        with open('data/mobs.csv', 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            fieldnames = reader.fieldnames
            if 'speed' not in fieldnames:
                fieldnames.append('speed')
            
            for row in reader:
                if 'speed' not in row or not row['speed']:
                    # Default mob speed
                    diff = int(row.get('difficulty', 1))
                    row['speed'] = 20 + (diff * 10)
                rows.append(row)
                
        with open('data/mobs.csv', 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)
        print("Updated mobs.csv")
        
    except Exception as e:
        print(f"Error updating mobs.csv: {e}")

    # Bosses
    try:
        rows = []
        with open('data/bosses.csv', 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            fieldnames = reader.fieldnames
            if 'speed' not in fieldnames:
                fieldnames.append('speed')
            
            for row in reader:
                if 'speed' not in row or not row['speed']:
                    row['speed'] = 70 # Base boss speed
                rows.append(row)
                
        with open('data/bosses.csv', 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)
        print("Updated bosses.csv")
        
    except Exception as e:
        print(f"Error updating bosses.csv: {e}")

def migrate_db():
    print("Migrating Database...")
    try:
        conn = sqlite3.connect('points.db')
        cursor = conn.cursor()
        
        # Check if column exists in mob
        try:
            cursor.execute("SELECT speed FROM mob LIMIT 1")
        except sqlite3.OperationalError:
            print("Adding speed to mob table...")
            cursor.execute("ALTER TABLE mob ADD COLUMN speed INTEGER DEFAULT 30")
            
        # Check if column exists in raid
        try:
            cursor.execute("SELECT speed FROM raid LIMIT 1")
        except sqlite3.OperationalError:
            print("Adding speed to raid table...")
            cursor.execute("ALTER TABLE raid ADD COLUMN speed INTEGER DEFAULT 70")
            
        conn.commit()
        conn.close()
        print("Database migration complete.")
        
    except Exception as e:
        print(f"Error migrating database: {e}")

if __name__ == "__main__":
    migrate_csvs()
    migrate_db()
