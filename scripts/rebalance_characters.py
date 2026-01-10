import csv
import os

def rebalance_prices():
    input_file = 'data/characters.csv'
    output_file = 'data/characters_new.csv'
    
    if not os.path.exists(input_file):
        print(f"Error: {input_file} not found")
        return

    with open(input_file, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames
        rows = list(reader)

    for row in rows:
        level = int(row['livello'])
        # Quadratic scaling: price = 200 + (level - 1)^2 * 8
        # This gives ~200 at lv 1 and ~50,000 at lv 80
        new_price = 200 + ((level - 1) ** 2) * 8
        
        # Round to nearest 10 for cleaner prices
        new_price = round(new_price, -1)
        
        # Special characters or premium might have different logic, 
        # but the user asked to proportion everything.
        # If price was 0 (starter), keep it 0 or set to 200?
        # The user said "i primi personaggi devono costare circa 200 300 wumpa"
        # So even the first ones should have a price now, except maybe the very first starter?
        # Let's keep 0 as 0 if it's a starter (level 1 and price was 0).
        if int(row['price']) == 0 and level == 1:
            row['price'] = '0'
        else:
            row['price'] = str(int(new_price))

    with open(output_file, 'w', encoding='utf-8', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    os.replace(output_file, input_file)
    print("✅ Character prices rebalanced successfully!")

if __name__ == "__main__":
    rebalance_prices()
