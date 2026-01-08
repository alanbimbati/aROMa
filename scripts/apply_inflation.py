import csv
import os

def apply_inflation():
    files_to_update = [
        {'path': 'data/potions.csv', 'price_col': 'prezzo'},
        {'path': 'data/characters.csv', 'price_col': 'price'},
        {'path': 'data/transformations.csv', 'price_col': 'wumpa_cost'}
    ]
    
    for file_info in files_to_update:
        path = file_info['path']
        price_col = file_info['price_col']
        
        if not os.path.exists(path):
            print(f"File not found: {path}")
            continue
            
        print(f"Updating {path}...")
        
        rows = []
        with open(path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            fieldnames = reader.fieldnames
            for row in reader:
                try:
                    current_price = int(row[price_col])
                    row[price_col] = str(current_price * 4)
                except ValueError:
                    pass # Skip if not a number (e.g. empty)
                rows.append(row)
        
        with open(path, 'w', encoding='utf-8', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)
            
        print(f"Updated {len(rows)} rows in {path}")

if __name__ == "__main__":
    apply_inflation()
