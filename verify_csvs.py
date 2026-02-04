import csv
import os

files = ['data/characters.csv', 'data/mobs.csv', 'data/bosses.csv', 'items.csv']

def check_csv(filename):
    print(f"Checking {filename}...")
    if not os.path.exists(filename):
        print(f"❌ {filename} not found!")
        return

    try:
        with open(filename, 'r', encoding='utf-8') as f:
            reader = csv.reader(f)
            header = next(reader)
            expected_cols = len(header)
            
            row_count = 0
            for i, row in enumerate(reader, 1):
                if len(row) != expected_cols:
                    print(f"❌ Row {i} has {len(row)} columns, expected {expected_cols}: {row}")
                row_count += 1
            print(f"✅ {filename}: {row_count} rows, format OK.")
            
    except Exception as e:
        print(f"❌ Error reading {filename}: {e}")

for f in files:
    check_csv(f)
